import datetime
import logging
import os
import json
import shutil
import time
import csv
from typing import List, Optional, Any, Dict
from dataclasses import asdict

from core.models.test_data import TestMetaData
from core.models.test_state import TestState
from core.models.sensor_enum import SensorId
from core.models.circular_buffer import SensorDataStorage
from core.event_hub import event_hub
from core.processing.data_processor import PROCESSING_RATE

logger = logging.getLogger(__name__)

# Get the project root (3 levels up from this file: test_manager.py -> services -> core -> src -> project_root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
STORAGE_ROOT = os.path.join(PROJECT_ROOT, "storage", "data")
TEST_DATA_DIR = os.path.join(STORAGE_ROOT, "test_data")
ARCHIVE_DIR = os.path.join(STORAGE_ROOT, "archived_data")

# Sampling frequency per sensor type (Hz - points per second)
# Used to calculate buffer capacity and reference array sizes
# Default: 20 Hz (50ms between points)
SENSOR_SAMPLING_FREQ = 20.0


class TestManager:
    def __init__(self):
        self.current_test: Optional[TestMetaData] = None
        self.is_running = False
        self.test_history: List[TestMetaData] = []
        
        # Sensor data storage using efficient circular buffers
        # Indexed by SensorId.value for O(1) access
        # Point spacing is determined by DataProcessor publishing rate (PROCESSING_RATE),
        # not raw sensor frequency. If raw > processing rate, effective freq = processing rate.
        effective_freq = min(PROCESSING_RATE, SENSOR_SAMPLING_FREQ)  # Frames delivered at this rate, so spacing is based on this
        self.data_storage = SensorDataStorage(len(list(SensorId)), effective_freq)
        
        self.start_time = 0.0
        
        # File handles
        self.raw_file = None           # raw.log - raw serial input
        self.csv_file = None           # data.csv - calibrated sensor data
        self.csv_writer = None
        self.raw_csv_file = None       # raw_data.csv - uncalibrated sensor data
        self.raw_csv_writer = None
        self.current_test_dir = None

        # Ensure dirs
        os.makedirs(TEST_DATA_DIR, exist_ok=True)
        os.makedirs(ARCHIVE_DIR, exist_ok=True)

        # Load history
        self.reload_history()

        # Subscribe
        event_hub.subscribe("serial_data", self._on_serial_data)
        event_hub.subscribe("processed_data", self._on_processed_data)
        event_hub.subscribe("sensor_raw_update", self._on_raw_sensor_data)

    def reload_history(self):
        """Scans the disk for existing tests."""
        self.test_history = []
        logger.warning(f"[RELOAD] Scanning {TEST_DATA_DIR}")
        
        if not os.path.exists(TEST_DATA_DIR):
            logger.warning(f"[RELOAD] Directory does not exist: {TEST_DATA_DIR}")
            return

        items = os.listdir(TEST_DATA_DIR)
        logger.warning(f"[RELOAD] Found {len(items)} items in directory")
        
        for dirname in items:
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
                            logger.warning(f"[RELOAD] Loaded test {dirname}")
                    except Exception as e:
                        logger.error(f"Failed to load test {dirname}: {e}")
        
        # Sort by date (desc)
        self.test_history.sort(key=lambda x: x.date, reverse=True)
        logger.warning(f"[RELOAD] Finished loading {len(self.test_history)} tests")
        event_hub.send_all_on_topic("history_updated", None)

    def get_test_state(self) -> TestState:
        """
        Get the current state of the test system.
        
        Returns:
            TestState.NOTHING: No test running and no test prepared
            TestState.PREPARED: No test running but metadata has been set
            TestState.RUNNING: A test is currently running
        """
        if self.is_running:
            return TestState.RUNNING
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
        final_id = f"{safe_id}_{timestamp}"
        
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
        
        event_hub.send_all_on_topic("test_prepared", metadata)

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
        
        # Open CSV file for calibrated data
        self.csv_file = open(os.path.join(self.current_test_dir, "data.csv"), 'w', newline='')
        # We don't know columns yet, will init on first frame or hardcode
        self.csv_writer = None
        
        # Open CSV file for raw data
        self.raw_csv_file = open(os.path.join(self.current_test_dir, "raw_data.csv"), 'w', newline='')
        self.raw_csv_writer = None
        
        self.is_running = True
        # Clear data storage for new test
        self.data_storage.clear_all()
        self.start_time = datetime.datetime.now().timestamp()
        
        logger.info(f"Test started: {metadata.test_id}")
        event_hub.send_all_on_topic("test_started", metadata)
        event_hub.send_all_on_topic("test_state_changed", True)

    def stop_test(self):
        if self.current_test is None:
            return

        logger.info(f"Test stopped/cancelled: {self.current_test.test_id}")
        
        # Close files if running
        if self.is_running:
            if self.raw_file:
                self.raw_file.close()
                self.raw_file = None
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
            if self.raw_csv_file:
                self.raw_csv_file.close()
                self.raw_csv_file = None
                self.csv_writer = None
            
            self.reload_history() # Refresh list
            self.is_running = False
        
        # Clear data storage for next test
        self.data_storage.clear_all()
        
        temp_test = self.current_test
        self.current_test = None
        self.current_test_dir = None
        
        event_hub.send_all_on_topic("test_stopped", temp_test)
        event_hub.send_all_on_topic("test_state_changed", False)

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

    def _on_serial_data(self, topic, line):
        if self.is_running and self.raw_file:
            # Timestamp locally
            ts = datetime.datetime.now().isoformat()
            self.raw_file.write(f"[{ts}] {line}\n")

    def _on_raw_sensor_data(self, topic, sensor_data):
        """Handle raw (uncalibrated) sensor data from SensorManager."""
        if not self.is_running or not self.raw_csv_file:
            return
        
        t = sensor_data.timestamp
        rel_time = t - self.start_time
        sensor_id = sensor_data.sensor_id
        value = sensor_data.value
        
        # Initialize CSV writer on first raw data
        if self.raw_csv_writer is None:
            headers = ["timestamp", "relative_time", "sensor_id", "raw_value"]
            self.raw_csv_writer = csv.DictWriter(self.raw_csv_file, fieldnames=headers)
            self.raw_csv_writer.writeheader()
        
        row = {
            "timestamp": t,
            "relative_time": rel_time,
            "sensor_id": sensor_id.name,
            "raw_value": value
        }
        self.raw_csv_writer.writerow(row)
        self.raw_csv_file.flush()

    def _on_processed_data(self, topic, frame):
        """Frame format: {"timestamp": float, "values": dict, ...}"""
        if not self.is_running:
            return

        t = frame["timestamp"]
        rel_time = t - self.start_time
        values = frame["values"]
        
        # CSV Writing
        if self.csv_file:
            if self.csv_writer is None:
                # Init header - convert SensorId enum keys to their names for CSV
                headers = ["timestamp", "relative_time"] + sorted([sensor.name for sensor in SensorId])
                self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=headers)
                self.csv_writer.writeheader()
            
            row = {"timestamp": t, "relative_time": rel_time}
            # Convert enum keys to string names for CSV compatibility
            for sensor_id in SensorId:
                row[sensor_id.name] = values[sensor_id.value]
            self.csv_writer.writerow(row)
            self.csv_file.flush()

        # Store data in circular buffers
        # Append (relative_time, value) tuples for each sensor
        for sensor_id in SensorId:
            self.data_storage.append(
                sensor_id.value,
                rel_time,
                values[sensor_id.value]
            )

    def get_sensor_history(self, sensor_id: SensorId, window_seconds: int):
        """Return recent data for a sensor over the requested window (seconds)."""
        if not self.is_running:
            raise RuntimeError("No test is currently running")
        return self.data_storage.get_data_for_window_seconds(sensor_id.value, window_seconds)

    def get_history(self) -> List[TestMetaData]:
        """Get list of all test histories, reloaded from disk."""
        logger.warning("[GET_HISTORY] Called - reloading from disk")
        self.reload_history()
        logger.warning(f"[GET_HISTORY] Returning {len(self.test_history)} tests")
        return self.test_history

    def get_relative_time(self) -> float:
        """Get current time relative to test start, or 0.0 if no test is running."""
        if self.is_running and self.start_time > 0:
            return time.time() - self.start_time
        return 0.0

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

# Global instance
test_manager = TestManager()
