import datetime
import logging
import os
import json
import shutil
import time
import csv
from typing import List, Optional, Any, Dict
from dataclasses import asdict
import io

from PIL import Image, ImageDraw, ImageFont

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
SENSOR_SAMPLING_FREQ = 10.0


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
        effective_freq = PROCESSING_RATE
        self.data_storage = SensorDataStorage(len(list(SensorId)), effective_freq)
        
        self.start_time = 0.0
        
        # File handles
        self.raw_file = None           # raw.log - raw serial input
        self.csv_file = None           # data.csv - calibrated sensor data
        self.csv_writer = None
        self.raw_csv_file = None       # raw_data.csv - uncalibrated sensor data
        self.raw_csv_writer = None
        self.current_test_dir = None
        
        # PIL Images for graphiques (DISP_1 and ARC)
        self.graphique_disp1_image = None
        self.graphique_disp1_draw = None
        self.graphique_arc_image = None
        self.graphique_arc_draw = None
        self.graphique_width = 1000
        self.graphique_height = 700
        self.graphique_margin = 50
        self.graphique_disp1_last_point = None  # Track last point for DISP_1 line drawing
        self.graphique_arc_last_point = None    # Track last point for ARC line drawing

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
        event_hub.send_all_on_topic("history_updated", None)

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
        
        # Initialize both graphiques (DISP_1 and ARC)
        # DISP_1 graphique
        self.graphique_disp1_image = Image.new('RGBA', (self.graphique_width, self.graphique_height), (255, 255, 255, 0))
        self.graphique_disp1_draw = ImageDraw.Draw(self.graphique_disp1_image)
        self.graphique_disp1_last_point = None
        # ARC graphique
        self.graphique_arc_image = Image.new('RGBA', (self.graphique_width, self.graphique_height), (255, 255, 255, 0))
        self.graphique_arc_draw = ImageDraw.Draw(self.graphique_arc_image)
        self.graphique_arc_last_point = None
        # Draw axes on both
        self._draw_graphique_axes('DISP_1')
        self._draw_graphique_axes('ARC')
        
        self.is_running = True
        # Clear data storage for new test
        self.data_storage.clear_all()
        self.start_time = datetime.datetime.now().timestamp()
        
        logger.info(f"Test started: {metadata.test_id}")
        event_hub.send_all_on_topic("test_started", metadata)
        event_hub.send_all_on_topic("test_state_changed", True)

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
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        if self.raw_csv_file:
            self.raw_csv_file.close()
            self.raw_csv_file = None
            self.csv_writer = None
        
        # Save graphiques to test directory
        self._save_graphiques()
        
        # Mark as stopped but keep in memory
        self.is_running = False
        self.is_stopped = True
        
        temp_test = self.current_test
        event_hub.send_all_on_topic("test_stopped", temp_test)
        event_hub.send_all_on_topic("test_state_changed", False)

    def finalize_test(self):
        """Move stopped test to history and clear current test."""
        if self.current_test is None:
            raise ValueError("No test to finalize.")
        
        if not self.is_stopped:
            raise RuntimeError("Test is not stopped. Call PUT /stop first.")
        
        logger.info(f"Test finalized: {self.current_test.test_id}")
        
        # Clean up PIL images
        self.graphique_disp1_image = None
        self.graphique_disp1_draw = None
        self.graphique_disp1_last_point = None
        self.graphique_arc_image = None
        self.graphique_arc_draw = None
        self.graphique_arc_last_point = None
        
        # Clear data storage
        self.data_storage.clear_all()
        
        temp_test = self.current_test
        self.current_test = None
        self.current_test_dir = None
        self.is_stopped = False
        
        # Reload history now that the test is finalized and cleared from memory
        self.reload_history()
        
        event_hub.send_all_on_topic("test_finalized", temp_test)

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
        
        # Plot points on both graphiques
        disp1_value = values[SensorId.DISP_1.value]
        arc_value = values[SensorId.ARC.value]
        force_value = values[SensorId.FORCE.value]
        
        # Debug: log values occasionally
        if int(rel_time * 10) % 20 == 0:  # Every 2 seconds
            logger.info(f"Graph values - DISP_1: {disp1_value:.3f}, ARC: {arc_value:.3f}, FORCE: {force_value:.3f}")
        
        self._plot_point_on_graphique('DISP_1', disp1_value, force_value)
        self._plot_point_on_graphique('ARC', arc_value, force_value)
        
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
        return 0.0

    def _draw_graphique_axes(self, sensor_name: str):
        """Draw X and Y axes on the graphique with labels and units.
        
        Args:
            sensor_name: Either 'DISP_1' or 'ARC' to determine which graphique to draw on
        """
        if sensor_name == 'DISP_1':
            draw = self.graphique_disp1_draw
            x_label = "DISP_1 (mm)"
            x_max = 15.0
            x_min = 0.0
        elif sensor_name == 'ARC':
            draw = self.graphique_arc_draw
            x_label = "ARC (mm)"
            x_max = 5.0  # ARC range: -5 to +5 mm
            x_min = -5.0
        else:
            return
        
        if draw is None:
            return
        
        # Axis color (black)
        axis_color = 'black'
        axis_width = 4
        text_color = 'black'
        
        # Try to use a default font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # X axis (bottom)
        x_axis_y = self.graphique_height - self.graphique_margin
        draw.line(
            [(self.graphique_margin, x_axis_y), 
             (self.graphique_width - self.graphique_margin, x_axis_y)],
            fill=axis_color,
            width=axis_width
        )
        
        # Y axis (left)
        y_axis_x = self.graphique_margin
        draw.line(
            [(y_axis_x, self.graphique_margin), 
             (y_axis_x, self.graphique_height - self.graphique_margin)],
            fill=axis_color,
            width=axis_width
        )
        
        # Draw ticks and labels on X axis
        tick_size = 10
        tick_interval = 2 if sensor_name == 'ARC' else 3  # ARC: every 2, DISP_1: every 3
        x_range = x_max - x_min
        
        # Generate tick values based on range
        if sensor_name == 'ARC':
            tick_values = range(int(x_min), int(x_max) + 1, tick_interval)
        else:
            tick_values = range(int(x_min), int(x_max) + 1, tick_interval)
        
        for x_val in tick_values:
            # Map x_val to pixel position
            pixel_x = self.graphique_margin + ((x_val - x_min) / x_range) * (self.graphique_width - 2 * self.graphique_margin)
            # Draw tick
            draw.line(
                [(pixel_x, x_axis_y), (pixel_x, x_axis_y + tick_size)],
                fill=axis_color,
                width=3
            )
            # Draw label
            label = str(x_val)
            draw.text(
                (pixel_x - 15, x_axis_y + tick_size + 10),
                label,
                fill=text_color,
                font=font_small
            )
        
        # X axis label
        draw.text(
            (self.graphique_width - 220, self.graphique_height - 30),
            x_label,
            fill=text_color,
            font=font
        )
        
        # Draw ticks and labels on Y axis (FORCE: 0-1000 N)
        force_max = 1000.0
        force_interval = 200  # Every 200 units
        
        for force_val in range(0, int(force_max) + 1, force_interval):
            pixel_y = self.graphique_height - self.graphique_margin - (force_val / force_max) * (self.graphique_height - 2 * self.graphique_margin)
            # Draw tick
            draw.line(
                [(y_axis_x - tick_size, pixel_y), (y_axis_x, pixel_y)],
                fill=axis_color,
                width=3
            )
            # Draw label
            label = str(int(force_val))
            draw.text(
                (y_axis_x - 55, pixel_y - 10),
                label,
                fill=text_color,
                font=font_small
            )
        
        # Y axis label
        draw.text(
            (5, 10),
            "FORCE (N)",
            fill=text_color,
            font=font
        )

    def _plot_point_on_graphique(self, sensor_name: str, x_value: float, force: float):
        """Add a point to the graphique (X=sensor_value, Y=FORCE) and draw line to previous point.
        
        Args:
            sensor_name: Either 'DISP_1' or 'ARC' to determine which graphique to plot on
            x_value: The X-axis value (DISP_1 or ARC value)
            force: The Y-axis value (FORCE)
        """
        if not self.is_running:
            return
        
        # Select appropriate graphique
        if sensor_name == 'DISP_1':
            draw = self.graphique_disp1_draw
            last_point = self.graphique_disp1_last_point
            x_max = 15.0
            x_min = 0.0
        elif sensor_name == 'ARC':
            draw = self.graphique_arc_draw
            last_point = self.graphique_arc_last_point
            x_max = 5.0
            x_min = -5.0
        else:
            return
        
        if draw is None:
            return
        
        # Scaling parameters
        force_max = 1000.0
        x_range = x_max - x_min
        
        # Convert data to pixel coordinates
        # X axis: left margin to right margin
        pixel_x = self.graphique_margin + ((x_value - x_min) / x_range) * (self.graphique_width - 2 * self.graphique_margin)
        # Y axis: inverted (top is 0, bottom is max)
        pixel_y = self.graphique_height - self.graphique_margin - (force / force_max) * (self.graphique_height - 2 * self.graphique_margin)
        
        # Clamp to canvas bounds
        pixel_x = max(self.graphique_margin, min(self.graphique_width - self.graphique_margin, pixel_x))
        pixel_y = max(self.graphique_margin, min(self.graphique_height - self.graphique_margin, pixel_y))
        
        current_point = (pixel_x, pixel_y)
        
        # Draw line from last point to current point
        if last_point is not None:
            draw.line(
                [last_point, current_point],
                fill='black',
                width=4
            )
        
        # Update last point
        if sensor_name == 'DISP_1':
            self.graphique_disp1_last_point = current_point
        else:
            self.graphique_arc_last_point = current_point

    def _save_graphiques(self):
        """Save both graphiques as PNG files in the test directory."""
        if self.current_test_dir is None:
            logger.warning("Cannot save graphiques: no test directory")
            return
        
        # Save DISP_1 graphique
        if self.graphique_disp1_image is not None:
            disp1_path = os.path.join(self.current_test_dir, "graph_DISP_1.png")
            try:
                self.graphique_disp1_image.save(disp1_path, format='PNG')
                logger.info(f"Saved DISP_1 graphique to {disp1_path}")
            except Exception as e:
                logger.error(f"Failed to save DISP_1 graphique: {e}")
        
        # Save ARC graphique
        if self.graphique_arc_image is not None:
            arc_path = os.path.join(self.current_test_dir, "graph_ARC.png")
            try:
                self.graphique_arc_image.save(arc_path, format='PNG')
                logger.info(f"Saved ARC graphique to {arc_path}")
            except Exception as e:
                logger.error(f"Failed to save ARC graphique: {e}")

    def get_graphique_png(self, sensor_name: str) -> bytes:
        """Return the graphique as PNG bytes.
        
        Args:
            sensor_name: Either 'DISP_1' or 'ARC' to determine which graphique to return
        """
        if sensor_name == 'DISP_1':
            image = self.graphique_disp1_image
        elif sensor_name == 'ARC':
            image = self.graphique_arc_image
        else:
            image = None
        
        if image is None:
            # Return a blank canvas if no test running
            image = Image.new('RGBA', (self.graphique_width, self.graphique_height), (255, 255, 255, 0))
        
        # Convert to PNG bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()

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
