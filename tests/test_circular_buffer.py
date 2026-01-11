"""
Tests for CircularBuffer and SensorDataStorage efficiency
"""
import pytest
from src.core.models.circular_buffer import CircularBuffer, SensorDataStorage, DisplayDuration


class TestCircularBuffer:
    """Test CircularBuffer basic operations"""

    def test_append_and_get(self) -> None:
        """Test basic append and get operations"""
        buffer = CircularBuffer(capacity=5)
        
        buffer.append(1.0, 10.0)
        buffer.append(2.0, 20.0)
        buffer.append(3.0, 30.0)
        
        assert buffer.size() == 3
        assert buffer.get(0) == (1.0, 10.0)
        assert buffer.get(1) == (2.0, 20.0)
        assert buffer.get(2) == (3.0, 30.0)

    def test_circular_wrap_around(self) -> None:
        """Test that buffer wraps around correctly"""
        buffer = CircularBuffer(capacity=3)
        
        buffer.append(1.0, 10.0)
        buffer.append(2.0, 20.0)
        buffer.append(3.0, 30.0)
        
        # Add more data - should wrap around
        buffer.append(4.0, 40.0)  # Overwrites oldest (1.0, 10.0)
        buffer.append(5.0, 50.0)  # Overwrites (2.0, 20.0)
        
        assert buffer.size() == 3
        assert buffer.is_full()
        # Should now contain (3.0, 30.0), (4.0, 40.0), (5.0, 50.0)
        assert buffer.get(0) == (3.0, 30.0)
        assert buffer.get(1) == (4.0, 40.0)
        assert buffer.get(2) == (5.0, 50.0)

    def test_get_all(self) -> None:
        """Test getting all entries"""
        buffer = CircularBuffer(capacity=4)
        
        buffer.append(1.0, 10.0)
        buffer.append(2.0, 20.0)
        buffer.append(3.0, 30.0)
        
        all_data = buffer.get_all()
        assert len(all_data) == 3
        assert all_data == [(1.0, 10.0), (2.0, 20.0), (3.0, 30.0)]

    def test_get_range(self) -> None:
        """Test getting a range of entries"""
        buffer = CircularBuffer(capacity=5)
        
        for i in range(1, 6):
            buffer.append(float(i), float(i * 10))
        
        # Get entries 1 to 3 (indices)
        range_data = buffer.get_range(1, 4)
        assert len(range_data) == 3
        assert range_data == [(2.0, 20.0), (3.0, 30.0), (4.0, 40.0)]

    def test_clear(self) -> None:
        """Test clearing the buffer"""
        buffer = CircularBuffer(capacity=5)
        
        buffer.append(1.0, 10.0)
        buffer.append(2.0, 20.0)
        assert buffer.size() == 2
        
        buffer.clear()
        assert buffer.size() == 0


class TestSensorDataStorage:
    """Test SensorDataStorage with multiple sensors"""

    def test_initialization(self) -> None:
        """Test storage initialization with correct capacity"""
        storage = SensorDataStorage(sensor_count=4, sampling_frequency=20.0)
        
        # Capacity = 20 Hz * 30s * 20 = 12000 points
        assert storage.total_capacity == 12000
        assert len(storage.buffers) == 4

    def test_reference_arrays(self) -> None:
        """Test reference array sizes - all same points, different spacing"""
        storage = SensorDataStorage(sensor_count=4, sampling_frequency=20.0)
        
        # All arrays should have same number of points
        # Points = 20 Hz * 30s = 600
        expected_points = 600
        
        # Verify all durations have same number of points
        for duration in DisplayDuration:
            ref_info = storage.reference_arrays[duration]
            assert ref_info["points"] == expected_points
        
        # Verify spacing changes per duration
        assert storage.reference_arrays[DisplayDuration.DURATION_30S]["spacing"] == 30 / 600   # 0.05
        assert storage.reference_arrays[DisplayDuration.DURATION_1MIN]["spacing"] == 60 / 600  # 0.1
        assert storage.reference_arrays[DisplayDuration.DURATION_2MIN]["spacing"] == 120 / 600  # 0.2
        assert storage.reference_arrays[DisplayDuration.DURATION_5MIN]["spacing"] == 300 / 600  # 0.5
        assert storage.reference_arrays[DisplayDuration.DURATION_10MIN]["spacing"] == 600 / 600  # 1.0

    def test_append_multiple_sensors(self) -> None:
        """Test appending data to multiple sensors"""
        storage = SensorDataStorage(sensor_count=4, sampling_frequency=20.0)
        
        # Append data to sensor 0 (FORCE)
        storage.append(0, 1.0, 100.0)
        storage.append(0, 2.0, 200.0)
        
        # Append data to sensor 1 (DISP_1)
        storage.append(1, 1.0, 10.0)
        storage.append(1, 2.0, 20.0)
        
        assert len(storage.get_data(0)) == 2
        assert len(storage.get_data(1)) == 2
        assert storage.get_data(0) == [(1.0, 100.0), (2.0, 200.0)]
        assert storage.get_data(1) == [(1.0, 10.0), (2.0, 20.0)]

    def test_get_data_for_duration(self) -> None:
        """Test getting data for specific durations with uniform spacing"""
        storage = SensorDataStorage(sensor_count=4, sampling_frequency=20.0)
        
        # Simulate 40 seconds of data (800 points at 20 Hz)
        for i in range(800):
            time = i * 0.05  # 20 Hz = 50ms intervals
            value = float(i)
            storage.append(0, time, value)
        
        # All durations should return same number of points (600)
        data_30s = storage.get_data_for_duration(0, DisplayDuration.DURATION_30S)
        data_1min = storage.get_data_for_duration(0, DisplayDuration.DURATION_1MIN)
        data_2min = storage.get_data_for_duration(0, DisplayDuration.DURATION_2MIN)
        
        assert len(data_30s) == 600
        assert len(data_1min) == 600
        assert len(data_2min) == 600

    def test_clear_single_sensor(self) -> None:
        """Test clearing a single sensor"""
        storage = SensorDataStorage(sensor_count=4, sampling_frequency=20.0)
        
        storage.append(0, 1.0, 100.0)
        storage.append(1, 1.0, 10.0)
        
        assert len(storage.get_data(0)) == 1
        assert len(storage.get_data(1)) == 1
        
        storage.clear_sensor(0)
        assert len(storage.get_data(0)) == 0
        assert len(storage.get_data(1)) == 1

    def test_clear_all(self) -> None:
        """Test clearing all sensors"""
        storage = SensorDataStorage(sensor_count=4, sampling_frequency=20.0)
        
        for sensor_idx in range(4):
            storage.append(sensor_idx, 1.0, float(sensor_idx * 10))
        
        storage.clear_all()
        
        for sensor_idx in range(4):
            assert len(storage.get_data(sensor_idx)) == 0

    def test_buffer_stats(self) -> None:
        """Test getting buffer statistics"""
        storage = SensorDataStorage(sensor_count=4, sampling_frequency=20.0)
        
        storage.append(0, 1.0, 100.0)
        storage.append(0, 2.0, 200.0)
        
        stats = storage.get_sensor_buffer_stats(0)
        assert stats["capacity"] == 12000
        assert stats["current_count"] == 2
        assert stats["is_full"] is False
        assert stats["utilization"] == 2 / 12000

    def test_different_sampling_frequencies(self) -> None:
        """Test storage with different sampling frequencies"""
        storage_10hz = SensorDataStorage(sensor_count=4, sampling_frequency=10.0)
        storage_50hz = SensorDataStorage(sensor_count=4, sampling_frequency=50.0)
        
        # 10 Hz: 10 * 30 * 20 = 6000 capacity, 10 * 30 = 300 reference points
        assert storage_10hz.total_capacity == 6000
        assert storage_10hz.reference_points_count == 300
        assert storage_10hz.reference_arrays[DisplayDuration.DURATION_30S]["spacing"] == 30 / 300  # 0.1
        
        # 50 Hz: 50 * 30 * 20 = 30000 capacity, 50 * 30 = 1500 reference points
        assert storage_50hz.total_capacity == 30000
        assert storage_50hz.reference_points_count == 1500
        assert storage_50hz.reference_arrays[DisplayDuration.DURATION_30S]["spacing"] == 30 / 1500  # 0.02
