import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


CLIENT_DIR = Path(__file__).resolve().parents[2] / "Client"


class FakeCRCError(Exception):
    pass


class FakeMissingDataError(Exception):
    pass


class TestClientDHT22(unittest.TestCase):
    def setUp(self):
        self.original_path = list(sys.path)
        self.original_module = sys.modules.get("dht22")
        self.original_driver = sys.modules.get("dht22_takemoto")

        self.fake_sensor = MagicMock()
        self.fake_sensor.close = MagicMock()
        fake_driver = types.SimpleNamespace(
            DHT22=MagicMock(return_value=self.fake_sensor),
            DHT22CRCError=FakeCRCError,
            DHT22MissingDataError=FakeMissingDataError,
        )
        sys.modules["dht22_takemoto"] = fake_driver
        sys.modules.pop("dht22", None)
        sys.path.insert(0, str(CLIENT_DIR))
        self.dht22 = importlib.import_module("dht22")
        self.addCleanup(self._restore_imports)

    def _restore_imports(self):
        sys.path[:] = self.original_path
        if self.original_module is None:
            sys.modules.pop("dht22", None)
        else:
            sys.modules["dht22"] = self.original_module

        if self.original_driver is None:
            sys.modules.pop("dht22_takemoto", None)
        else:
            sys.modules["dht22_takemoto"] = self.original_driver

    def test_get_dht_data_with_status_returns_current_value(self):
        self.fake_sensor.read.return_value = (24.5, 60.0, None)

        result = self.dht22.get_dht_data_with_status()

        self.assertEqual(result, (24.5, 60.0, "ok", None))

    def test_get_dht_data_with_status_uses_recent_value_after_retry_failure(self):
        self.fake_sensor.read.return_value = (24.5, 60.0, None)
        self.dht22.get_dht_data_with_status()
        self.fake_sensor.read.side_effect = FakeCRCError("bad checksum")

        with patch.object(self.dht22.time, "sleep") as mock_sleep:
            result = self.dht22.get_dht_data_with_status()

        self.assertEqual(result, (24.5, 60.0, "stale", "CRC"))
        self.assertEqual(mock_sleep.call_count, self.dht22.READ_RETRY_COUNT - 1)

    def test_get_dht_data_with_status_raises_when_no_recent_value_exists(self):
        self.fake_sensor.read.side_effect = FakeMissingDataError("no pulse")

        with patch.object(self.dht22.time, "sleep"), self.assertRaises(
            self.dht22.DHT22ReadError
        ) as context:
            self.dht22.get_dht_data_with_status()

        self.assertEqual(context.exception.error_code, "missing_data")

    def test_close_closes_sensor_instance(self):
        self.dht22.close()

        self.fake_sensor.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
