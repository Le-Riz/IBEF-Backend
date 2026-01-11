import datetime
import logging
import os
import json
import shutil
import csv
from typing import List, Optional, Any, Dict
from dataclasses import asdict

from core.models.test_data import TestMetaData
from core.models.sensor_enum import SensorId
from core.models.circular_buffer import SensorDataStorage
from core.event_hub import event_hub
from core.processing.data_processor import PROCESSING_RATE

logger = logging.getLogger(__name__)

STORAGE_ROOT = "storage/data"
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
        self.raw_file = None
        self.csv_file = None
        self.csv_writer = None
        self.current_test_dir = None

        # Ensure dirs
        os.makedirs(TEST_DATA_DIR, exist_ok=True)
        os.makedirs(ARCHIVE_DIR, exist_ok=True)

        # Load history
        self.reload_history()

        # Subscribe
        event_hub.subscribe("serial_data", self._on_serial_data)
        event_hub.subscribe("processed_data", self._on_processed_data)

    def reload_history(self):
        """Scans the disk for existing tests."""
        self.test_history = []
        if not os.path.exists(TEST_DATA_DIR):
            return

        for dirname in os.listdir(TEST_DATA_DIR):
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
                    except Exception as e:
                        logger.error(f"Failed to load test {dirname}: {e}")
        
        # Sort by date (desc)
        self.test_history.sort(key=lambda x: x.date, reverse=True)
        event_hub.send_all_on_topic("history_updated", None)

    def prepare_test(self, metadata: TestMetaData):
        """Sets the test as current but does not start it yet."""
        if self.is_running:
            raise RuntimeError("A test is already running.")
        
        self.current_test = metadata
        event_hub.send_all_on_topic("test_prepared", metadata)

    def start_test(self, metadata: Optional[TestMetaData] = None):
        if self.is_running:
            raise RuntimeError("A test is already running.")
        
        # Use prepared test if no metadata provided
        if metadata is None:
            if self.current_test is None:
                raise ValueError("No test prepared and no metadata provided.")
            metadata = self.current_test
        
        # Ensure unique ID with timestamp if needed, or trust input.
        # Let's clean the ID for filesystem safety
        safe_id = "".join([c for c in metadata.test_id if c.isalnum() or c in ('-','_')])
        if not safe_id: safe_id = "test"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        final_id = f"{safe_id}_{timestamp}"
        
        # Update metadata to reflect the actual ID and timestamp we use
        metadata.test_id = final_id
        
        self.current_test = metadata
        self.current_test_dir = os.path.join(TEST_DATA_DIR, final_id)
        os.makedirs(self.current_test_dir, exist_ok=True)
        
        # Save Metadata
        with open(os.path.join(self.current_test_dir, "metadata.json"), 'w') as f:
            json.dump(asdict(metadata), f, indent=2)

        # Open raw file
        self.raw_file = open(os.path.join(self.current_test_dir, "raw.log"), 'w', buffering=1) # Line buffered
        
        # Open CSV file
        self.csv_file = open(os.path.join(self.current_test_dir, "data.csv"), 'w', newline='')
        # We don't know columns yet, will init on first frame or hardcode
        self.csv_writer = None
        
        self.is_running = True
        # Clear data storage for new test
        self.data_storage.clear_all()
        self.start_time = datetime.datetime.now().timestamp()
        
        logger.info(f"Test started: {final_id}")
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

    def get_history(self) -> List[TestMetaData]:
        return self.test_history

    def _on_serial_data(self, topic, line):
        if self.is_running and self.raw_file:
            # Timestamp locally
            ts = datetime.datetime.now().isoformat()
            self.raw_file.write(f"[{ts}] {line}\n")

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

# Global instance
test_manager = TestManager()
