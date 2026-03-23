"""
file_writer.py — Background thread-based writer for CSV, raw log, and PIL graphique operations.

Decouples all file I/O and PIL drawing from the asyncio event loop to eliminate
jitter in the serial data pipeline.

All heavy operations (disk writes, PIL draw.line) are processed sequentially
in a single dedicated thread, ensuring:
  1. No thread-safety issues with PIL Image objects
  2. No event loop blocking from disk I/O
  3. Batched writes for better throughput
"""

import csv
import io
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


class _MsgType(Enum):
    """Internal message types for the writer queue."""
    RAW_LOG = auto()
    CSV_ROW = auto()
    PLOT = auto()
    STOP = auto()


@dataclass(slots=True)
class _WriterMsg:
    """Message sent to the writer thread."""
    msg_type: _MsgType
    payload: object = None


class FileWriter:
    """
    Background thread that handles all file I/O and PIL drawing operations.

    Usage:
        writer = FileWriter()
        writer.start(raw_path="/path/to/raw.log", csv_path="/path/to/raw_data.csv")
        writer.log_raw("[1234.56] FORCE ASC2 ...")
        writer.log_csv({"timestamp": "1234.560", "sensor_id": "FORCE", ...})
        writer.enqueue_plot(graphique_obj, x_value, y_value)
        writer.stop()  # Drains queue, closes files
    """

    # Maximum items to batch-dequeue per iteration for throughput
    _BATCH_SIZE = 64

    def __init__(self):
        self._queue: queue.Queue[_WriterMsg] = queue.Queue(maxsize=8192)
        self._thread: Optional[threading.Thread] = None

        # File handles (owned exclusively by the writer thread)
        self._raw_file = None
        self._csv_file = None
        self._csv_writer = None
        self._csv_headers_written = False

        # Stats
        self._write_count = 0
        self._drop_count = 0

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, raw_path: str, csv_path: str) -> None:
        """
        Start the background writer thread and open output files.

        Args:
            raw_path: Path to the raw log file.
            csv_path: Path to the CSV data file.
        """
        if self.is_running:
            logger.warning("FileWriter already running, stopping first.")
            self.stop()

        # Reset state
        self._write_count = 0
        self._drop_count = 0
        self._csv_headers_written = False

        # Open files (on the calling thread — these are fast operations)
        self._raw_file = open(raw_path, "w", buffering=8192)  # 8KB buffer
        self._csv_file = open(csv_path, "w", newline="", buffering=8192)
        self._csv_writer = None  # Initialized on first CSV row

        # Clear any leftover messages
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        self._thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="FileWriter",
        )
        self._thread.start()
        logger.info("FileWriter started.")

    def stop(self) -> None:
        """
        Signal the writer thread to stop, drain remaining messages, and close files.
        Blocks until the thread has fully exited.
        """
        if not self.is_running:
            return

        # Send stop sentinel
        try:
            self._queue.put(_WriterMsg(_MsgType.STOP), timeout=5.0)
        except queue.Full:
            logger.error("FileWriter queue full, forcing stop.")

        self._thread.join(timeout=10.0)
        if self._thread.is_alive():
            logger.error("FileWriter thread did not exit cleanly.")

        self._thread = None
        logger.info(
            "FileWriter stopped. Wrote %d entries, dropped %d.",
            self._write_count, self._drop_count,
        )

    def log_raw(self, line: str) -> None:
        """
        Enqueue a raw log line for writing. Non-blocking.

        Args:
            line: The raw log line (without trailing newline).
        """
        try:
            self._queue.put_nowait(_WriterMsg(_MsgType.RAW_LOG, line))
        except queue.Full:
            self._drop_count += 1

    def log_csv(self, row: dict) -> None:
        """
        Enqueue a CSV row dict for writing. Non-blocking.

        Args:
            row: Dict with column names matching the CSV headers.
        """
        try:
            self._queue.put_nowait(_WriterMsg(_MsgType.CSV_ROW, row))
        except queue.Full:
            self._drop_count += 1

    def enqueue_plot(self, graphique, x_value: float, y_value: float) -> None:
        """
        Enqueue a PIL draw.line operation. Non-blocking.

        Args:
            graphique: The Graphique object to plot on.
            x_value: X coordinate (data space).
            y_value: Y coordinate (data space).
        """
        try:
            self._queue.put_nowait(
                _WriterMsg(_MsgType.PLOT, (graphique, x_value, y_value))
            )
        except queue.Full:
            self._drop_count += 1

    # ---- Internal ----

    def _writer_loop(self) -> None:
        """Main writer loop: dequeues messages and processes them."""
        try:
            while True:
                # Block on the first message
                try:
                    msg = self._queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if msg.msg_type == _MsgType.STOP:
                    # Drain remaining messages before exiting
                    self._drain()
                    break

                self._process_msg(msg)

                # Batch-process additional available messages for throughput
                for _ in range(self._BATCH_SIZE - 1):
                    try:
                        msg = self._queue.get_nowait()
                    except queue.Empty:
                        break
                    if msg.msg_type == _MsgType.STOP:
                        self._drain()
                        return
                    self._process_msg(msg)

        except Exception as e:
            logger.error("FileWriter loop crashed: %s", e, exc_info=True)
        finally:
            self._close_files()

    def _process_msg(self, msg: _WriterMsg) -> None:
        """Process a single writer message."""
        try:
            if msg.msg_type == _MsgType.RAW_LOG:
                if self._raw_file:
                    self._raw_file.write(msg.payload + "\n")
                    self._write_count += 1

            elif msg.msg_type == _MsgType.CSV_ROW:
                if self._csv_file and isinstance(msg.payload, dict):
                    if self._csv_writer is None:
                        headers = list(msg.payload.keys())
                        self._csv_writer = csv.DictWriter(
                            self._csv_file, fieldnames=headers
                        )
                        self._csv_writer.writeheader()
                    self._csv_writer.writerow(msg.payload)
                    self._write_count += 1

            elif msg.msg_type == _MsgType.PLOT:
                graphique, x_val, y_val = msg.payload
                graphique.plot_point_on_graphique(x_val, y_val)
                self._write_count += 1

        except Exception as e:
            logger.error("FileWriter error processing message: %s", e)

    def _drain(self) -> None:
        """Drain all remaining messages from the queue."""
        while True:
            try:
                msg = self._queue.get_nowait()
                if msg.msg_type != _MsgType.STOP:
                    self._process_msg(msg)
            except queue.Empty:
                break

    def _close_files(self) -> None:
        """Flush and close all open file handles."""
        if self._raw_file:
            try:
                self._raw_file.flush()
                self._raw_file.close()
            except Exception as e:
                logger.error("Error closing raw file: %s", e)
            self._raw_file = None

        if self._csv_file:
            try:
                self._csv_file.flush()
                self._csv_file.close()
            except Exception as e:
                logger.error("Error closing CSV file: %s", e)
            self._csv_file = None

        self._csv_writer = None
