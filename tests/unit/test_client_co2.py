import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


CLIENT_DIR = Path(__file__).resolve().parents[2] / "Client"


class FakeSerialConnection:
    def __init__(self, response):
        self.response = response
        self.reset_input_buffer = MagicMock()
        self.reset_output_buffer = MagicMock()
        self.write = MagicMock()
        self.flush = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def read(self, size):
        return self.response


class TestClientCO2(unittest.TestCase):
    def setUp(self):
        self.original_path = list(sys.path)
        self.original_co2 = sys.modules.get("co2")
        self.original_serial = sys.modules.get("serial")
        self.serial_connection = None

        def serial_factory(*args, **kwargs):
            return self.serial_connection

        self.fake_serial = types.SimpleNamespace(
            EIGHTBITS=8,
            PARITY_NONE="N",
            STOPBITS_ONE=1,
            Serial=MagicMock(side_effect=serial_factory),
        )
        sys.modules["serial"] = self.fake_serial
        sys.modules.pop("co2", None)
        sys.path.insert(0, str(CLIENT_DIR))
        self.co2 = importlib.import_module("co2")
        self.addCleanup(self._restore_imports)

    def _restore_imports(self):
        sys.path[:] = self.original_path
        if self.original_co2 is None:
            sys.modules.pop("co2", None)
        else:
            sys.modules["co2"] = self.original_co2

        if self.original_serial is None:
            sys.modules.pop("serial", None)
        else:
            sys.modules["serial"] = self.original_serial

    def _response(self, ppm):
        response = bytearray([0xFF, 0x86, ppm // 256, ppm % 256, 0, 0, 0, 0, 0])
        response[8] = self.co2._checksum(response)
        return bytes(response)

    def test_checksum_matches_mhz19_formula(self):
        self.assertEqual(self.co2._checksum(bytes.fromhex("ff 86 03 e8 00 00 00 00 8f")), 0x8F)

    def test_read_co2_once_returns_ppm_from_valid_response(self):
        self.serial_connection = FakeSerialConnection(self._response(1000))

        with patch.object(self.co2.time, "sleep"):
            result = self.co2._read_co2_once()

        self.assertEqual(result, 1000)
        self.fake_serial.Serial.assert_called_once_with(
            self.co2.SERIAL_DEVICE,
            baudrate=self.co2.BAUD_RATE,
            bytesize=self.fake_serial.EIGHTBITS,
            parity=self.fake_serial.PARITY_NONE,
            stopbits=self.fake_serial.STOPBITS_ONE,
            timeout=1.0,
        )
        self.serial_connection.write.assert_called_once_with(self.co2.READ_COMMAND)
        self.serial_connection.flush.assert_called_once_with()

    def test_read_co2_once_accepts_8_byte_response_without_prefix(self):
        self.serial_connection = FakeSerialConnection(self._response(1200)[1:])

        with patch.object(self.co2.time, "sleep"):
            result = self.co2._read_co2_once()

        self.assertEqual(result, 1200)

    def test_read_co2_once_rejects_invalid_length(self):
        self.serial_connection = FakeSerialConnection(b"\xff\x86")

        with patch.object(self.co2.time, "sleep"), self.assertRaisesRegex(
            self.co2.CO2ReadError, "Invalid response length"
        ):
            self.co2._read_co2_once()

    def test_read_co2_once_rejects_invalid_header(self):
        response = bytearray(self._response(1000))
        response[1] = 0x85
        response[8] = self.co2._checksum(response)
        self.serial_connection = FakeSerialConnection(bytes(response))

        with patch.object(self.co2.time, "sleep"), self.assertRaisesRegex(
            self.co2.CO2ReadError, "Invalid CO2 sensor response header"
        ):
            self.co2._read_co2_once()

    def test_read_co2_once_rejects_invalid_checksum(self):
        response = bytearray(self._response(1000))
        response[8] ^= 0xFF
        self.serial_connection = FakeSerialConnection(bytes(response))

        with patch.object(self.co2.time, "sleep"), self.assertRaisesRegex(
            self.co2.CO2ReadError, "Invalid CO2 sensor checksum"
        ):
            self.co2._read_co2_once()

    def test_get_co2_data_waits_for_warmup_then_returns_int(self):
        self.co2._initialized_time = 100.0

        with patch.object(self.co2.time, "time", return_value=105.0):
            with patch.object(self.co2.time, "sleep") as mock_sleep:
                with patch.object(self.co2, "_read_co2_once", return_value=1000):
                    result = self.co2.get_co2_data()

        self.assertEqual(result, 1000)
        mock_sleep.assert_called_once_with(5.0)

    def test_get_co2_data_retries_and_raises_after_failures(self):
        with patch.object(self.co2.time, "time", return_value=self.co2._initialized_time + 99):
            with patch.object(self.co2.time, "sleep") as mock_sleep:
                with patch.object(
                    self.co2,
                    "_read_co2_once",
                    side_effect=RuntimeError("serial failed"),
                ) as mock_read:
                    with self.assertRaisesRegex(
                        self.co2.CO2ReadError, "CO2 sensor read failed"
                    ):
                        self.co2.get_co2_data()

        self.assertEqual(mock_read.call_count, self.co2.READ_RETRY_COUNT)
        self.assertEqual(mock_sleep.call_count, self.co2.READ_RETRY_COUNT)


if __name__ == "__main__":
    unittest.main()
