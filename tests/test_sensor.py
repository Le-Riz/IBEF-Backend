"""
Tests for sensor-specific functionality: raw data, zero calibration, and integration tests.
Basic sensor data endpoint tests are in test_data.py
"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestSensorRaw:
    """Test GET /api/sensor/{sensor_id}/raw - get latest raw (uncalibrated) sensor value"""

    def test_get_sensor_raw_data_force(self) -> None:
        """Test getting raw data from FORCE sensor"""
        response = client.get("/api/sensor/FORCE/raw")
        assert response.status_code == 200
        data = response.json()
        assert "time" in data
        assert "value" in data
        assert isinstance(data["time"], (int, float))
        assert isinstance(data["value"], (int, float))

    def test_get_sensor_raw_data_disp_1(self) -> None:
        """Test getting raw data from DISP_1 sensor"""
        response = client.get("/api/sensor/DISP_1/raw")
        assert response.status_code == 200
        data = response.json()
        assert "time" in data
        assert "value" in data

    def test_get_sensor_raw_data_disp_2(self) -> None:
        """Test getting raw data from DISP_2 sensor"""
        response = client.get("/api/sensor/DISP_2/raw")
        assert response.status_code == 200
        data = response.json()
        assert "time" in data
        assert "value" in data

    def test_get_sensor_raw_data_disp_3(self) -> None:
        """Test getting raw data from DISP_3 sensor"""
        response = client.get("/api/sensor/DISP_3/raw")
        assert response.status_code == 200
        data = response.json()
        assert "time" in data
        assert "value" in data

    def test_get_sensor_raw_data_disp_4(self) -> None:
        """Test getting raw data from DISP_4 sensor"""
        response = client.get("/api/sensor/DISP_4/raw")
        assert response.status_code == 200
        data = response.json()
        assert "time" in data
        assert "value" in data

    def test_get_sensor_raw_data_disp_5(self) -> None:
        """Test getting raw data from DISP_5 sensor"""
        response = client.get("/api/sensor/DISP_5/raw")
        assert response.status_code == 200
        data = response.json()
        assert "time" in data
        assert "value" in data

    def test_get_sensor_raw_data_invalid_id(self) -> None:
        """Test getting raw data with invalid sensor ID returns 400"""
        response = client.get("/api/sensor/INVALID_SENSOR/raw")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid sensor_id" in data["detail"]


class TestSensorZero:
    """Test PUT /api/sensor/{sensor_id}/zero - calibrate sensor by zeroing current value"""

    def test_zero_sensor_force(self) -> None:
        """Test zeroing the FORCE sensor"""
        response = client.put("/api/sensor/FORCE/zero")
        assert response.status_code == 204

    def test_zero_sensor_disp_1(self) -> None:
        """Test zeroing the DISP_1 sensor"""
        response = client.put("/api/sensor/DISP_1/zero")
        assert response.status_code == 204

    def test_zero_sensor_disp_2(self) -> None:
        """Test zeroing the DISP_2 sensor"""
        response = client.put("/api/sensor/DISP_2/zero")
        assert response.status_code == 204

    def test_zero_sensor_disp_3(self) -> None:
        """Test zeroing the DISP_3 sensor"""
        response = client.put("/api/sensor/DISP_3/zero")
        assert response.status_code == 204

    def test_zero_sensor_disp_4(self) -> None:
        """Test zeroing the DISP_4 sensor"""
        response = client.put("/api/sensor/DISP_4/zero")
        assert response.status_code == 204

    def test_zero_sensor_disp_5(self) -> None:
        """Test zeroing the DISP_5 sensor"""
        response = client.put("/api/sensor/DISP_5/zero")
        assert response.status_code == 204

    def test_zero_sensor_invalid_id(self) -> None:
        """Test zeroing with an invalid sensor ID returns 400"""
        response = client.put("/api/sensor/INVALID_SENSOR/zero")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid sensor_id" in data["detail"]


class TestSensorZeroIntegration:
    """Integration tests for zero functionality - verify offset behavior"""

    def test_zero_affects_raw_value(self) -> None:
        """Test that zeroing a sensor affects its raw value calculation"""
        # Get initial raw value for FORCE
        response1 = client.get("/api/sensor/FORCE/raw")
        assert response1.status_code == 200
        initial_raw = response1.json()["value"]

        # Get initial data value (corrected)
        response2 = client.get("/api/sensor/FORCE/data")
        assert response2.status_code == 200
        initial_corrected = response2.json()["value"]

        # Zero the sensor
        response_zero = client.put("/api/sensor/FORCE/zero")
        assert response_zero.status_code == 204

        # Get new raw value - should increase by the previous corrected value
        response3 = client.get("/api/sensor/FORCE/raw")
        assert response3.status_code == 200
        new_raw = response3.json()["value"]

        # raw_new should approximately equal raw_old + corrected_old
        # (allowing for sensor drift during the emulation)
        expected_raw_increase = initial_corrected
        assert abs((new_raw - initial_raw) - expected_raw_increase) < 1.0

    def test_zero_isolation_between_sensors(self) -> None:
        """Test that zeroing one sensor doesn't affect others"""
        # Get initial values for FORCE and DISP_1
        force_data_before = client.get("/api/sensor/FORCE/data").json()["value"]
        disp1_data_before = client.get("/api/sensor/DISP_1/data").json()["value"]

        # Zero FORCE sensor only
        response = client.put("/api/sensor/FORCE/zero")
        assert response.status_code == 204

        # Check that DISP_1 is unaffected
        disp1_raw_after = client.get("/api/sensor/DISP_1/raw").json()["value"]
        disp1_data_after = client.get("/api/sensor/DISP_1/data").json()["value"]

        # DISP_1 values should not have changed significantly
        # (allowing for normal sensor drift)
        assert abs(disp1_data_after - disp1_data_before) < 1.0

    def test_zero_all_sensors_independently(self) -> None:
        """Test that each sensor can be zeroed independently"""
        sensors = ["FORCE", "DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5"]

        for sensor_id in sensors:
            # Zero the sensor
            response = client.put(f"/api/sensor/{sensor_id}/zero")
            assert response.status_code == 204

            # Verify it returns 204 (no errors)
            # Verify we can still read from it
            response_data = client.get(f"/api/sensor/{sensor_id}/data")
            assert response_data.status_code == 200

            response_raw = client.get(f"/api/sensor/{sensor_id}/raw")
            assert response_raw.status_code == 200

    def test_zero_makes_data_close_to_zero(self) -> None:
        """Test that data value becomes close to 0 immediately after zeroing"""
        sensors = ["FORCE", "DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5"]

        for sensor_id in sensors:
            # Zero the sensor
            response_zero = client.put(f"/api/sensor/{sensor_id}/zero")
            assert response_zero.status_code == 204

            # Immediately get the data - should be close to 0
            response_data = client.get(f"/api/sensor/{sensor_id}/data")
            assert response_data.status_code == 200
            data_value = response_data.json()["value"]

            # Value should be very close to 0 (allowing for sensor drift)
            assert abs(data_value) < 0.5, f"Sensor {sensor_id} data value {data_value} is not close to 0"
