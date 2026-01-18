import pytest
from core.port_detector import PortDetector, port_detector


class TestPortDetectorIdentification:
    """Test sensor identification from serial data."""
    
    def test_identify_force_sensor(self):
        """Test identifying FORCE sensor from ASC2 format."""
        line = "ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00"
        result = PortDetector._identify_sensor_from_line(line)
        assert result == "FORCE"
    
    def test_identify_disp_sensor(self):
        """Test identifying DISP sensor from SPC_VAL format."""
        line = "76 144 262 us SPC_VAL usSenderId=0x2E01 ulMicros=76071216 Val=0.000"
        result = PortDetector._identify_sensor_from_line(line)
        assert result == "DISP"
    
    def test_identify_disp_variant(self):
        """Test identifying DISP with different values."""
        line = "100 200 300 us SPC_VAL usSenderId=0x2E02 ulMicros=100123456 Val=5.234"
        result = PortDetector._identify_sensor_from_line(line)
        assert result == "DISP"
    
    def test_unknown_format(self):
        """Test unrecognized format returns None."""
        line = "garbage data that doesn't match any format"
        result = PortDetector._identify_sensor_from_line(line)
        assert result is None
    
    def test_partial_force_format(self):
        """Test ASC2 with insufficient data returns None."""
        line = "ASC2 20945595"
        result = PortDetector._identify_sensor_from_line(line)
        assert result is None
    
    def test_partial_disp_format(self):
        """Test SPC_VAL without required fields returns None."""
        line = "SPC_VAL usSenderId=0x2E01"
        result = PortDetector._identify_sensor_from_line(line)
        assert result is None


class TestPortDetectorStructure:
    """Test PortDetector structure and methods."""
    
    def test_singleton_pattern(self):
        """Test PortDetector is a singleton."""
        detector1 = PortDetector()
        detector2 = PortDetector()
        assert detector1 is detector2
    
    def test_get_available_ports(self):
        """Test getting available ports."""
        ports = PortDetector.get_available_ports()
        assert isinstance(ports, list)
        # We can't assume specific ports exist, just check it doesn't crash
    
    def test_detected_sensors_initialization(self):
        """Test detected_sensors is initialized."""
        detector = PortDetector()
        assert isinstance(detector.detected_sensors, dict)
        assert isinstance(detector.port_to_sensor, dict)
    
    def test_get_detected_empty(self):
        """Test getting detected sensors when none have been found yet."""
        detector = PortDetector()
        detected = detector.get_all_detected()
        assert isinstance(detected, dict)
    
    def test_sensor_availability_check(self):
        """Test checking sensor availability."""
        detector = PortDetector()
        # Should return False for sensors that haven't been detected
        assert detector.is_sensor_available("NONEXISTENT") == False

