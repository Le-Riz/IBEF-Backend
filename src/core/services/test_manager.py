import datetime
import logging
import math
import os
import json
import shutil
import time
import csv
from typing import List, Optional
from dataclasses import asdict
import io

from PIL import Image, ImageDraw, ImageFont

from core.models.sensor_data import SensorData
from core.models.test_data import TestMetaData
from core.models.test_state import TestState
from core.models.sensor_enum import SensorId
from core.models.circular_buffer import SensorDataStorage
from core.config_loader import config_loader
from core.processing.graphique import Graphique, GraphiqueConfig
from core.services.sensor_manager import sensor_manager

logger = logging.getLogger(__name__)

# Get the project root (3 levels up from this file: test_manager.py -> services -> core -> src -> project_root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
STORAGE_ROOT = os.path.join(PROJECT_ROOT, "storage", "data")
TEST_DATA_DIR = os.path.join(STORAGE_ROOT, "test_data")
ARCHIVE_DIR = os.path.join(STORAGE_ROOT, "archived_data")

# Sampling frequency per sensor type (Hz - points per second)
# Used to calculate buffer capacity and reference array sizes
# Default: 20 Hz (50ms between points)
SENSOR_SAMPLING_FREQ = 5.0

PROCESSING_RATE = 4.0

class TestManager:
    def __init__(self):
        self.current_test: Optional[TestMetaData] = None
        self.is_running = False
        self.is_stopped = False  # Test has been stopped but not yet finalized
        self.test_history: List[TestMetaData] = []
        
        # Sensor data storage using efficient circular buffers
        # Indexed by SensorId.value for O(1) access
        # Point spacing is determined by DataProcessor publishing rate (PROCESSING_RATE),
        # not raw sensor frequency. If raw > processing rate, effective freq = processing rate.
        # Align buffer sampling with the processor publish rate to avoid underestimating window span
        self.data_storage = SensorDataStorage(len(list(SensorId)), SENSOR_SAMPLING_FREQ)
        
        self.start_time = 0.0
        
        # File handles
        self.raw_file = None           # raw.log - raw serial input
        self.raw_csv_file = None       # raw_data.csv - uncalibrated sensor data
        self.raw_csv_writer = None
        self.current_test_dir = None
        
        self.max_interpolation_gap = 0.5 # seconds - max gap between points to allow interpolation, otherwise leave blank in CSV
        
        # PIL Images for graphiques (DISP_1 and ARC)
        self.graphique_disp1 = Graphique(SensorId.DISP_1, SensorId.FORCE, GraphiqueConfig())
        self.graphique_arc = Graphique(SensorId.ARC, SensorId.FORCE, GraphiqueConfig(x_min=-5.0))

        self.graphique_disp1_history: tuple[SensorData, SensorData] = (SensorData(0.0, SensorId.DISP_1, math.nan), SensorData(0.0, SensorId.FORCE, math.nan))
        self.graphique_arc_history: tuple[SensorData, SensorData] = (SensorData(0.0, SensorId.ARC, math.nan), SensorData(0.0, SensorId.FORCE, math.nan))

        # Numeric output precision (decimals after the decimal point)
        # time: number of decimals for relative_time (seconds)
        # force: decimals for FORCE sensor
        # disp: decimals for displacement sensors (DISP_*, ARC)
        self.time_decimals = 3
        self.force_decimals = 2
        self.disp_decimals = 6

        # Ensure dirs
        os.makedirs(TEST_DATA_DIR, exist_ok=True)
        os.makedirs(ARCHIVE_DIR, exist_ok=True)

        self.files_added_to_current_test: list[str] = []

        # Emulation clock (used when no test is running)
        self.emulation_start_time: float | None = None

        # Load history
        self.reload_history()

        # Add write functions to receive data from SensorManager and processed data from DataProcessor
        sensor_manager.add_write_func(self._on_serial_data)
        
        sensor_manager.add_func_notify(self._on_raw_sensor_data)

    def reload_history(self):
        """Scans the disk for existing tests."""
        self.test_history = []
        logger.info(f"[RELOAD] Scanning {TEST_DATA_DIR}")
        
        if not os.path.exists(TEST_DATA_DIR):
            logger.info(f"[RELOAD] Directory does not exist: {TEST_DATA_DIR}")
            return

        items = os.listdir(TEST_DATA_DIR)
        logger.info(f"[RELOAD] Found {len(items)} items in directory")
        
        for dirname in items:
            # Do not surface the in-flight test (prepared/running/stopped) in history
            if self.current_test and dirname == self.current_test.test_id:
                logger.debug(f"[RELOAD] Skipping current in-progress test {dirname} from history")
                continue

            dirpath = os.path.join(TEST_DATA_DIR, dirname)
            if os.path.isdir(dirpath):
                meta_path = os.path.join(dirpath, "metadata.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r') as f:
                            data = json.load(f)
                            # Reconstruct dataclass (naive approach)
                            meta = TestMetaData(**data)
                            # Identify the real ID used as foldername if different
                            meta.test_id = dirname 
                            self.test_history.append(meta)
                            logger.debug(f"[RELOAD] Loaded test {dirname}")
                    except Exception as e:
                        logger.error(f"Failed to load test {dirname}: {e}")
        
        # Sort by date (desc)
        self.test_history.sort(key=lambda x: x.date, reverse=True)
        logger.info(f"[RELOAD] Finished loading {len(self.test_history)} tests")

    def get_test_state(self) -> TestState:
        """
        Get the current state of the test system.
        
        Returns:
            TestState.NOTHING: No test running and no test prepared
            TestState.PREPARED: No test running but metadata has been set
            TestState.RUNNING: A test is currently running
            TestState.STOPPED: A test has been stopped but not yet finalized
        """
        if self.is_running:
            return TestState.RUNNING
        elif self.is_stopped:
            return TestState.STOPPED
        elif self.current_test is not None:
            return TestState.PREPARED
        else:
            return TestState.NOTHING

    def prepare_test(self, metadata: TestMetaData):
        """Sets the test as current but does not start it yet. Creates the test directory and description file."""
        if self.is_running:
            raise RuntimeError("A test is already running.")
        
        # Generate unique test ID with timestamp
        safe_id = "".join([c for c in metadata.test_id if c.isalnum() or c in ('-','_')])
        if not safe_id: safe_id = "test"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        final_id = f"{timestamp}_{safe_id}"
        
        # Update metadata with final ID
        metadata.test_id = final_id
        self.current_test = metadata
        
        # Create test directory
        self.current_test_dir = os.path.join(TEST_DATA_DIR, final_id)
        os.makedirs(self.current_test_dir, exist_ok=True)
        
        # Save metadata
        with open(os.path.join(self.current_test_dir, "metadata.json"), 'w') as f:
            json.dump(asdict(metadata), f, indent=2)
        
        # Create default description.md file
        description_content = f"# {metadata.test_id}\n\nDescription de l'expérience.\n\n## Informations\n- Date: {metadata.date}\n- Opérateur: {metadata.operator_name}\n- Spécimen: {metadata.specimen_code}"
        with open(os.path.join(self.current_test_dir, "description.md"), 'w', encoding='utf-8') as f:
            f.write(description_content)

    def start_test(self):
        if self.is_running:
            raise RuntimeError("A test is already running.")
        
        # Use prepared test
        if self.current_test is None:
            raise ValueError("No test metadata prepared. Call POST /info first.")
        
        if self.current_test_dir is None:
            raise RuntimeError("Test directory not initialized. This should not happen.")
        
        metadata = self.current_test
        # Directory and metadata already created by prepare_test()

        # Open raw file
        self.raw_file = open(os.path.join(self.current_test_dir, "raw.log"), 'w', buffering=1) # Line buffered
        
        # Open CSV file for raw data
        self.raw_csv_file = open(os.path.join(self.current_test_dir, "raw_data.csv"), 'w', newline='')
        self.raw_csv_writer = None
        
        # Initialize both graphiques (DISP_1 and ARC)
        self.graphique_disp1.reset()
        self.graphique_arc.reset()
        
        self.is_running = True
        # Reset emulation clock when a real/recorded test starts
        self.emulation_start_time = None
        # Clear data storage for new test
        self.data_storage.clear_all()
        self.start_time = datetime.datetime.now().timestamp()
        
        logger.info(f"Test started: {metadata.test_id}")

    def stop_test(self):
        """Stop recording data but keep test in memory for review/finalization."""
        if self.current_test is None:
            return

        if not self.is_running:
            return  # Already stopped or not running

        logger.info(f"Test stopped (recording ended): {self.current_test.test_id}")
        
        # Close files to stop recording
        if self.raw_file:
            self.raw_file.close()
            self.raw_file = None
        if self.raw_csv_file:
            self.raw_csv_file.close()
            self.raw_csv_file = None
        
        # Save graphiques to test directory
        self.graphique_disp1.save_graphique(self.current_test_dir, "graphique_disp1.png")
        self.graphique_arc.save_graphique(self.current_test_dir, "graphique_arc.png")
        
        # Mark as stopped but keep in memory
        self.is_running = False
        self.is_stopped = True

    def calculate_interpolated_data(self):
        
        if self.current_test is None:
            raise RuntimeError("No test in memory to calculate data for.")
        
        if self.current_test_dir is None:
            raise RuntimeError("Test directory not initialized. This should not happen.")
        
        raw_csv = open(os.path.join(self.current_test_dir, "raw_data.csv"), 'r')
        data_csv = open(os.path.join(self.current_test_dir, "data.csv"), 'w', newline='')
        headers = ["timestamp", "relative_time"] + [sensor.name for sensor in SensorId]
        data_csv_writer = csv.DictWriter(data_csv, fieldnames=headers)
        data_csv_writer.writeheader()
        raw_list: list[list[tuple[float, float]]] = [[] for _ in SensorId]
        reader = csv.DictReader(raw_csv)
        
        for row in reader:
            try:
                # Handle legacy 'SensorId.FORCE' or standard 'FORCE' string
                sensor_id_str = row["sensor_id"].split('.')[-1]
                sensor_id = SensorId[sensor_id_str]
                timestamp = float(row["timestamp"])
                raw_value = float(row["raw_value"])
                offset = float(row["offset"])
                raw_list[sensor_id.value].append((timestamp, raw_value - offset))
            except Exception as e:
                logger.warning(f"Error parsing raw CSV row {row}: {e}")
        
        valid_end_times = [raw_list[sensor_id.value][-1][0] for sensor_id in SensorId if raw_list[sensor_id.value]]
        if not valid_end_times:
            data_csv.close()
            raw_csv.close()
            return
            
        end_time = max(valid_end_times)
        number_of_points = int((end_time - self.start_time) * PROCESSING_RATE)
        
        for i in range(0, number_of_points):
            wantedTime = self.start_time + i * (1/PROCESSING_RATE)
            line = {"timestamp": f"{wantedTime:.{self.time_decimals}f}", "relative_time": f"{wantedTime - self.start_time:.{self.time_decimals}f}"}
            for sensor_id in SensorId:
                data_points = raw_list[sensor_id.value]
                if not data_points:
                    continue
                # Find two points that sandwich the wantedTime
                before = None
                after = None
                for t, val in data_points:
                    if not math.isnan(t) and not math.isnan(val) and t < wantedTime:
                        before = (t, val)
                    elif not math.isnan(t) and not math.isnan(val) and t > wantedTime and before is not None:
                        after = (t, val)
                        break
                
                if before is not None and after is not None and after[0] - before[0] <= self.max_interpolation_gap:
                    t1, v1 = before
                    t2, v2 = after
                    interpolated_val = v1 + (v2 - v1) * (wantedTime - t1) / (t2 - t1)
                    logger.debug(f"Interpolated {sensor_id.name} at {wantedTime:.3f}s: {interpolated_val:.3f}")
                    line[sensor_id.name] = f"{interpolated_val:.{self.force_decimals if sensor_id == SensorId.FORCE else self.disp_decimals}f}"
                else:
                    line[sensor_id.name] = ""
                    
            data_csv_writer.writerow(line)
        data_csv.flush()
        raw_csv.close()
        data_csv.close()

    def finalize_test(self):
        """Move stopped test to history and clear current test."""
        if self.current_test is None:
            raise ValueError("No test to finalize.")
        
        if not self.is_stopped:
            raise RuntimeError("Test is not stopped. Call PUT /stop first.")
        
        logger.info(f"Test finalized: {self.current_test.test_id}")
        
        # Clean up PIL images
        self.graphique_disp1.reset()
        self.graphique_arc.reset()
        
        # Clear data storage
        self.data_storage.clear_all()
        
        self.calculate_interpolated_data()
        
        self.current_test = None
        self.current_test_dir = None
        self.is_stopped = False

        # Reset emulation clock to allow live time in simulation mode
        self.emulation_start_time = None
        
        self.files_added_to_current_test.clear()
        
        # Reload history now that the test is finalized and cleared from memory
        self.reload_history()

    def archive_test(self, test_id: str):
        """Moves a test folder to the archive directory."""
        src = os.path.join(TEST_DATA_DIR, test_id)
        dst = os.path.join(ARCHIVE_DIR, test_id)
        if os.path.exists(src):
            shutil.move(src, dst)
            self.reload_history()
            logger.info(f"Archived test {test_id}")
            return True
        return False

    def delete_test(self, test_id: str):
        """Irreversibly deletes a test."""
        target = os.path.join(TEST_DATA_DIR, test_id)
        if os.path.exists(target):
            shutil.rmtree(target)
            self.reload_history()
            logger.info(f"Deleted test {test_id}")
            return True
        return False

    def _on_serial_data(self, sensor_id: SensorId, time: float, line: str):
        if self.is_running and self.raw_file:
            self.raw_file.write(f"[{time}] {sensor_id.name} {line}\n")

    def _on_raw_sensor_data(self, sensor_data: SensorData):
        """Handle raw (uncalibrated) sensor data from SensorManager."""
        if not self.is_running or not self.raw_csv_file:
            return
        
        t = sensor_data.timestamp
        rel_time = t - self.start_time
        sensor_id = sensor_data.sensor_id
        value = sensor_data.value
        raw_value = sensor_data.raw_value
        
        if sensor_id == SensorId.DISP_1:
            self.graphique_disp1_history = (sensor_data, self.graphique_disp1_history[1])
            
            if not math.isnan(self.graphique_disp1_history[0].value) and not math.isnan(self.graphique_disp1_history[1].value):
                self.graphique_disp1.plot_point_on_graphique(self.graphique_disp1_history[0].value, self.graphique_disp1_history[1].value)
        
        elif sensor_id == SensorId.ARC:
            self.graphique_arc_history = (sensor_data, self.graphique_arc_history[1])
            
            if not math.isnan(self.graphique_arc_history[0].value) and not math.isnan(self.graphique_arc_history[1].value):
                self.graphique_arc.plot_point_on_graphique(self.graphique_arc_history[0].value, self.graphique_arc_history[1].value)
        
        elif sensor_id == SensorId.FORCE:
            self.graphique_disp1_history = (self.graphique_disp1_history[0], sensor_data)
            if not math.isnan(self.graphique_disp1_history[0].value) and not math.isnan(self.graphique_disp1_history[1].value):
                self.graphique_disp1.plot_point_on_graphique(self.graphique_disp1_history[0].value, self.graphique_disp1_history[1].value)
                
            self.graphique_arc_history = (self.graphique_arc_history[0], sensor_data)
            if not math.isnan(self.graphique_arc_history[0].value) and not math.isnan(self.graphique_arc_history[1].value):
                self.graphique_arc.plot_point_on_graphique(self.graphique_arc_history[0].value, self.graphique_arc_history[1].value)
        
        self._store_sensor_data(sensor_data)
        
        # Initialize CSV writer on first raw data
        if self.raw_csv_writer is None:
            headers = ["timestamp", "relative_time", "sensor_id", "raw_value", "offset"]
            self.raw_csv_writer = csv.DictWriter(self.raw_csv_file, fieldnames=headers)
            self.raw_csv_writer.writeheader()
        
        # Format numbers according to configured precision
        def _format_raw_value(sid_name: SensorId, val: float):
            if val is None:
                return ""
            if sid_name == SensorId.FORCE:
                return f"{val:.{self.force_decimals}f}"
            # DISP_* and ARC
            if SensorId.DISP_1 == sid_name or SensorId.DISP_2 == sid_name or SensorId.DISP_3 == sid_name or SensorId.DISP_4 == sid_name or SensorId.DISP_5 == sid_name or sid_name == SensorId.ARC:
                return f"{val:.{self.disp_decimals}f}"
            # Default
            return f"{val:.{self.force_decimals}f}"

        row = {
            "timestamp": f"{t:.{self.time_decimals}f}",
            "relative_time": f"{rel_time:.{self.time_decimals}f}",
            "sensor_id": sensor_id.name,
            "raw_value": _format_raw_value(sensor_id, raw_value),
            "offset": _format_raw_value(sensor_id, sensor_data.offset)
        }
        self.raw_csv_writer.writerow(row)

    def _store_sensor_data(self, data: SensorData, epsilon: float = 1e-6):
        """Store data in circular buffers
        Append (relative_time, value) tuples for each sensor
        Only append points that respect the storage sampling frequency.
        For each sensor, check the last recorded point time and ensure the
        new point's relative time is >= last_time + spacing (with small epsilon)."""
        sensor_idx = data.sensor_id.value
        val = data.value
        spacing = 1.0 / float(self.data_storage.sampling_frequency)
        rel_time = data.timestamp - self.start_time
        
        if not math.isnan(val):
            buffer = self.data_storage.buffers[sensor_idx]
            if buffer.size() == 0:
                # buffer empty -> always append
                self.data_storage.append(sensor_idx, rel_time, val)
            else:
                # Get last recorded time (logical index = size-1)
                last_time, _ = buffer.get(buffer.size() - 1)
                expected_time = last_time + spacing
                if rel_time + epsilon >= expected_time:
                    self.data_storage.append(sensor_idx, rel_time, val)
                
    def get_sensor_history(self, sensor_id: SensorId, window_seconds: int):
        """Return recent data for a sensor over the requested window (seconds)."""
        # Allow history access while a test is stopped but not yet finalized
        if not (self.is_running or self.is_stopped):
            raise RuntimeError("No test is currently running or stopped")
        return self.data_storage.get_data_for_window_seconds(sensor_id.value, window_seconds)

    def get_history(self) -> List[TestMetaData]:
        """Get list of all test histories, reloaded from disk."""
        logger.debug("[GET_HISTORY] Called - reloading from disk")
        self.reload_history()
        logger.debug(f"[GET_HISTORY] Returning {len(self.test_history)} tests")
        return self.test_history

    def get_relative_time(self) -> float:
        """Get current time relative to test start, or 0.0 if no test is running."""
        if self.is_running and self.start_time > 0:
            return time.time() - self.start_time

        # In simulation mode (no test running), expose a monotonic clock so time does not stay at 0
        try:
            from core.services.sensor_manager import sensor_manager
        except Exception:
            sensor_manager = None

        if sensor_manager and sensor_manager.emulated_sensors:
            if self.emulation_start_time is None:
                self.emulation_start_time = time.time()
            return time.time() - self.emulation_start_time

        return 0.0

    def get_graphique_png(self, sensor_name: str) -> bytes:
        """Return the graphique as PNG bytes.
        
        Args:
            sensor_name: Either 'DISP_1' or 'ARC' to determine which graphique to return
        """
        
        if sensor_name == 'DISP_1':
            return self.graphique_disp1.get_graphique_png()
        
        else:
            return self.graphique_arc.get_graphique_png()

    def get_description(self, test_id: str) -> str:
        """Get the description.md content for a test."""
        desc_path = os.path.join(TEST_DATA_DIR, test_id, "description.md")
        if os.path.exists(desc_path):
            with open(desc_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # If not found in test_data, try archived_data
        desc_path = os.path.join(ARCHIVE_DIR, test_id, "description.md")
        if os.path.exists(desc_path):
            with open(desc_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        raise FileNotFoundError(f"Description not found for test {test_id}")

    def set_description(self, test_id: str, content: str) -> bool:
        """Update the description.md content for a test."""
        # Try test_data first
        desc_path = os.path.join(TEST_DATA_DIR, test_id, "description.md")
        if os.path.exists(desc_path):
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated description for test {test_id}")
            return True
        
        # Try archived_data
        desc_path = os.path.join(ARCHIVE_DIR, test_id, "description.md")
        if os.path.exists(desc_path):
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated description for archived test {test_id}")
            return True
        
        return False
    
    def add_file(self, file: bytes, filename: str) -> bool:
        """Add a file to the current test directory."""
        if self.current_test_dir is None:
            return False
        
        self.files_added_to_current_test.append(filename)
        file_path = os.path.join(self.current_test_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(file)
        logger.info(f"Added file {filename} to test {self.current_test.test_id}")  # type: ignore
        return True
    
    def list_files(self) -> List[str]:
        """List files added to the current test (excluding raw.log and description.md)."""
        if self.current_test_dir is None:
            return []
        
        # Return the list of files added via add_file, excluding raw.log and description.md
        return self.files_added_to_current_test
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file that was added to the current test."""
        if self.current_test_dir is None:
            return False

        if filename not in self.files_added_to_current_test:
            return False

        file_path = os.path.join(self.current_test_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        self.files_added_to_current_test.remove(filename)
        logger.info(f"Deleted file {filename} from test {self.current_test.test_id}")  # type: ignore
        return True

    def get_file(self, filename: str) -> Optional[bytes]:
        """Get the content of a file added to the current test."""
        if self.current_test_dir is None:
            return None
        
        if filename not in self.files_added_to_current_test:
            return None
        
        file_path = os.path.join(self.current_test_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read()
        
        return None

# Global instance
test_manager = TestManager()
