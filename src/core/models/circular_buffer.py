"""
CircularBuffer for efficient time-series data storage with O(1) access and insertion.
Optimized for speed: precomputed indices, vectorized operations where possible.
Supports reference arrays for different time windows with uniform point spacing.
"""
from typing import List, Tuple
from enum import Enum


class DisplayDuration(Enum):
    """Enum for display durations in seconds"""
    DURATION_30S = 30
    DURATION_1MIN = 60
    DURATION_2MIN = 120
    DURATION_5MIN = 300
    DURATION_10MIN = 600

    def value_seconds(self) -> int:
        """Get duration in seconds"""
        return self.value


class CircularBuffer:
    """
    Efficient circular buffer for storing (time, value) tuples.
    - O(1) insertion at the end
    - O(1) random access
    - Fixed capacity, overwrites oldest when full
    - Optimized for speed: pre-allocated buffer, direct indexing
    """

    __slots__ = ('capacity', 'buffer', 'write_index', 'count', '_mask')

    def __init__(self, capacity: int):
        """
        Initialize circular buffer.
        
        Args:
            capacity: Maximum number of (time, value) tuples to store
        """
        self.capacity = capacity
        self.buffer: List[Tuple[float, float]] = [(0.0, 0.0)] * capacity
        self.write_index = 0  # Next position to write
        self.count = 0  # Number of valid entries (0 to capacity)
        # Precompute mask for power-of-2 capacities (faster modulo)
        self._mask = capacity - 1 if (capacity & (capacity - 1)) == 0 else None

    def append(self, time: float, value: float) -> None:
        """Add a (time, value) tuple to the buffer. O(1)."""
        self.buffer[self.write_index] = (time, value)
        # Fast modulo if power of 2; else standard
        if self._mask is not None:
            self.write_index = (self.write_index + 1) & self._mask
        else:
            self.write_index = (self.write_index + 1) % self.capacity
        if self.count < self.capacity:
            self.count += 1

    def get(self, index: int) -> Tuple[float, float]:
        """
        Get item at logical index (0 = oldest, count-1 = newest).
        O(1) access.
        """
        if index < 0 or index >= self.count:
            raise IndexError(f"Index {index} out of range [0, {self.count})")
        # Direct computation: no loop, no extra calculations
        if self._mask is not None:
            physical_index = (self.write_index - self.count + index) & self._mask
        else:
            physical_index = (self.write_index - self.count + index) % self.capacity
        return self.buffer[physical_index]

    def get_all(self) -> List[Tuple[float, float]]:
        """Get all valid entries in chronological order. Optimized for bulk retrieval."""
        if self.count == 0:
            return []
        
        # Pre-allocate result list with placeholder tuples
        result: List[Tuple[float, float]] = [(0.0, 0.0)] * self.count
        
        # If buffer is not wrapped, direct slice is faster
        if self.write_index >= self.count:
            # Simple case: all data is contiguous
            start = self.write_index - self.count
            for i in range(self.count):
                result[i] = self.buffer[start + i]
        else:
            # Wrapped case: split into two parts
            first_part_size = self.capacity - (self.write_index - self.count)
            # First part: from (write_index - count) to end
            start_idx = self.capacity - (self.count - self.write_index)
            for i in range(first_part_size):
                result[i] = self.buffer[start_idx + i]
            # Second part: from start to write_index
            for i in range(self.count - first_part_size):
                result[first_part_size + i] = self.buffer[i]
        
        return result

    def get_range(self, start_index: int, end_index: int) -> List[Tuple[float, float]]:
        """Get entries from start_index to end_index (exclusive). Optimized retrieval."""
        if start_index < 0 or end_index > self.count or start_index > end_index:
            raise IndexError(f"Invalid range [{start_index}, {end_index}) for buffer of size {self.count}")
        
        range_size = end_index - start_index
        if range_size == 0:
            return []
        
        result: List[Tuple[float, float]] = [(0.0, 0.0)] * range_size
        
        # Compute physical indices for start and end
        if self._mask is not None:
            phys_start = (self.write_index - self.count + start_index) & self._mask
            phys_end = (self.write_index - self.count + end_index) & self._mask
        else:
            phys_start = (self.write_index - self.count + start_index) % self.capacity
            phys_end = (self.write_index - self.count + end_index) % self.capacity
        
        # Check if range wraps
        if phys_start <= phys_end or (phys_start > phys_end and phys_end <= phys_start):
            # No wrap: contiguous in buffer
            if phys_start < phys_end:
                for i in range(range_size):
                    result[i] = self.buffer[phys_start + i]
            else:
                # Wrapped: first part from phys_start to end, then from 0 to phys_end
                first_part = self.capacity - phys_start
                for i in range(first_part):
                    result[i] = self.buffer[phys_start + i]
                for i in range(phys_end):
                    result[first_part + i] = self.buffer[i]
        else:
            # Simple wrap case
            for i in range(range_size):
                if self._mask is not None:
                    idx = (phys_start + i) & self._mask
                else:
                    idx = (phys_start + i) % self.capacity
                result[i] = self.buffer[idx]
        
        return result

    def is_full(self) -> bool:
        """Check if buffer is at capacity."""
        return self.count == self.capacity

    def size(self) -> int:
        """Get number of valid entries."""
        return self.count

    def clear(self) -> None:
        """Clear all entries."""
        self.write_index = 0
        self.count = 0


class SensorDataStorage:
    """
    Stores time-series data for all sensors with circular buffers and reference arrays.
    Heavily optimized for speed with precomputed offsets and direct indexing.
    
    Each sensor gets indexed by sensor_id.value for O(1) access.
    All reference arrays have the SAME number of points but different spacing.
    """

    __slots__ = ('sensor_count', 'sampling_frequency', 'total_capacity', 'buffers',
                 'reference_points_count', 'reference_arrays', 'reference_offsets',
                 '_duration_to_enum', '_precomputed_windows')

    def __init__(self, sensor_count: int, sampling_frequency: float):
        """
        Initialize sensor data storage with precomputed structures for speed.
        
        Args:
            sensor_count: Number of sensors (e.g., 4 for FORCE, DISP_1, DISP_2, DISP_3)
            sampling_frequency: Sampling frequency in Hz (points per second)
        """
        self.sensor_count = sensor_count
        self.sampling_frequency = sampling_frequency

        # Calculate capacity: frequency × 30s × 20 = 10 minutes of data
        points_per_30s = int(sampling_frequency * 30)
        total_capacity = points_per_30s * 20
        self.total_capacity = total_capacity

        # Create circular buffers for each sensor
        self.buffers: List[CircularBuffer] = [
            CircularBuffer(total_capacity) for _ in range(sensor_count)
        ]

        # Number of reference points (same for all durations)
        self.reference_points_count = points_per_30s

        # Precompute all window information at init time
        self.reference_arrays = {}
        self.reference_offsets = {}
        self._duration_to_enum = {}
        self._precomputed_windows = {}

        for duration in DisplayDuration:
            duration_seconds = duration.value_seconds()
            window_seconds = duration_seconds
            
            # Store duration -> seconds mapping for O(1) lookup
            self._duration_to_enum[window_seconds] = duration
            
            # Spacing info
            spacing = duration_seconds / self.reference_points_count
            self.reference_arrays[duration] = {
                "duration": duration_seconds,
                "points": self.reference_points_count,
                "spacing": spacing,
            }

            # Precompute offsets and window info
            max_points_in_window = int(self.sampling_frequency * duration_seconds)
            target_points = self.reference_points_count
            
            if target_points <= 0 or max_points_in_window <= 0:
                self.reference_offsets[duration] = []
                self._precomputed_windows[window_seconds] = None
            else:
                # Precompute offsets
                step = max_points_in_window / target_points
                offsets: List[int] = []
                for i in range(target_points):
                    idx = int(i * step)
                    if i == target_points - 1:
                        idx = max_points_in_window - 1
                    offsets.append(idx)
                
                self.reference_offsets[duration] = offsets
                
                # Store precomputed window info
                self._precomputed_windows[window_seconds] = {
                    "max_points": max_points_in_window,
                    "offsets": offsets,
                    "duration_enum": duration,
                }

    def append(self, sensor_idx: int, time: float, value: float) -> None:
        """Add a data point to a sensor's buffer. O(1)."""
        if sensor_idx < 0 or sensor_idx >= self.sensor_count:
            raise ValueError(f"Invalid sensor index {sensor_idx}")
        self.buffers[sensor_idx].append(time, value)

    def get_data(self, sensor_idx: int) -> List[Tuple[float, float]]:
        """Get all data points for a sensor."""
        if sensor_idx < 0 or sensor_idx >= self.sensor_count:
            raise ValueError(f"Invalid sensor index {sensor_idx}")
        return self.buffers[sensor_idx].get_all()

    def get_data_for_duration(
        self, sensor_idx: int, duration: DisplayDuration
    ) -> List[Tuple[float, float]]:
        """
        Get data points for a specific display duration with uniform spacing.
        Returns up to reference_points_count points evenly spaced across the duration.
        """
        if duration not in DisplayDuration:
            raise ValueError(f"Invalid duration: {duration}")
        return self.get_data_for_window_seconds(sensor_idx, duration.value_seconds())

    def get_data_for_window_seconds(self, sensor_idx: int, window_seconds: int) -> List[Tuple[float, float]]:
        """
        Retrieve data for a given time window (in seconds) with uniform spacing.
        Optimized: uses precomputed offsets and direct indexing, no dynamic computation.
        """
        if sensor_idx < 0 or sensor_idx >= self.sensor_count:
            raise ValueError(f"Invalid sensor index {sensor_idx}")

        # Fast lookup with precomputed window info
        window_info = self._precomputed_windows.get(window_seconds)
        if window_info is None:
            raise ValueError(f"Unsupported window_seconds: {window_seconds}")

        buffer = self.buffers[sensor_idx]
        if buffer.size() == 0:
            return []

        max_points_in_window = window_info["max_points"]
        offsets = window_info["offsets"]
        
        available_points = min(buffer.size(), max_points_in_window)
        target_points = self.reference_points_count

        # Case 1: Not enough points yet - fallback to partial sampling
        if available_points <= target_points:
            start_idx = buffer.size() - available_points
            return buffer.get_range(start_idx, buffer.size())

        # Case 2: Full window available - use precomputed offsets (fast path)
        if available_points >= max_points_in_window:
            window_start_idx = buffer.size() - max_points_in_window
            result: List[Tuple[float, float]] = [(0.0, 0.0)] * len(offsets)
            
            # Direct indexed access using precomputed offsets
            for i, off in enumerate(offsets):
                result[i] = buffer.get(window_start_idx + off)
            return result

        # Case 3: Partial window - subsample available points
        step = available_points / target_points
        start_idx = buffer.size() - available_points
        result: List[Tuple[float, float]] = [(0.0, 0.0)] * target_points
        
        for i in range(target_points):
            idx = int(start_idx + i * step)
            if i == target_points - 1:
                idx = start_idx + available_points - 1
            result[i] = buffer.get(idx)
        
        return result

    def clear_sensor(self, sensor_idx: int) -> None:
        """Clear data for a specific sensor."""
        if sensor_idx < 0 or sensor_idx >= self.sensor_count:
            raise ValueError(f"Invalid sensor index {sensor_idx}")
        self.buffers[sensor_idx].clear()

    def clear_all(self) -> None:
        """Clear all sensor data."""
        for buffer in self.buffers:
            buffer.clear()

    def get_sensor_buffer_stats(self, sensor_idx: int) -> dict:
        """Get statistics about a sensor's buffer."""
        if sensor_idx < 0 or sensor_idx >= self.sensor_count:
            raise ValueError(f"Invalid sensor index {sensor_idx}")
        buffer = self.buffers[sensor_idx]
        return {
            "capacity": buffer.capacity,
            "current_count": buffer.count,
            "is_full": buffer.is_full(),
            "utilization": buffer.count / buffer.capacity,
        }
