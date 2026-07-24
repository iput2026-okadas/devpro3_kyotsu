import importlib
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


CLIENT_DIR = Path(__file__).resolve().parents[2] / "Client"


class TestClient(unittest.TestCase):
    def setUp(self):
        self.original_path = list(sys.path)
        self.original_modules = {
            name: sys.modules.get(name) for name in ("client", "co2", "dht22", "light")
        }

        self.dht22 = types.SimpleNamespace(
            get_dht_data_with_status=MagicMock(
                return_value=(24.5, 60.0, "ok", None)
            ),
            close=MagicMock(),
        )
        self.co2 = types.SimpleNamespace(
            get_co2_data=MagicMock(return_value=900),
            close=MagicMock(),
        )
        self.light = types.SimpleNamespace(
            get_light_percent=MagicMock(return_value=55.5),
        )

        sys.modules["dht22"] = self.dht22
        sys.modules["co2"] = self.co2
        sys.modules["light"] = self.light
        sys.modules.pop("client", None)
        sys.path.insert(0, str(CLIENT_DIR))
        self.client = importlib.import_module("client")
        self.addCleanup(self._restore_imports)

    def _restore_imports(self):
        sys.path[:] = self.original_path
        for name, original in self.original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_parse_arguments_reads_client_id_host_and_port(self):
        arguments = self.client.parse_arguments(
            ["-i", " raspi-lab ", "-h", "192.0.2.10", "-p", "9000"]
        )

        self.assertEqual(arguments.client_id, "raspi-lab")
        self.assertEqual(arguments.host, "192.0.2.10")
        self.assertEqual(arguments.port, 9000)

        long_options = self.client.parse_arguments(
            ["--client-id", "raspi-office"]
        )
        self.assertEqual(long_options.client_id, "raspi-office")

    def test_parse_arguments_requires_non_empty_client_id(self):
        for arguments in ([], ["-i", "   "]):
            with self.subTest(arguments=arguments):
                with patch("sys.stderr", new_callable=io.StringIO):
                    with self.assertRaises(SystemExit):
                        self.client.parse_arguments(arguments)

    def test_read_sensors_returns_expected_json_schema(self):
        result = self.client.read_sensors()

        self.assertEqual(
            result,
            {
                "temp": 24.5,
                "humid": 60.0,
                "co2": 900,
                "light_percent": 55.5,
            },
        )

    def test_read_sensors_keeps_other_values_when_dht22_fails(self):
        self.dht22.get_dht_data_with_status.side_effect = RuntimeError("dht failed")

        with patch("sys.stdout"):
            result = self.client.read_sensors()

        self.assertIsNone(result["temp"])
        self.assertIsNone(result["humid"])
        self.assertEqual(result["co2"], 900)
        self.assertEqual(result["light_percent"], 55.5)

    def test_read_sensors_keeps_other_values_when_co2_fails(self):
        self.co2.get_co2_data.side_effect = RuntimeError("co2 failed")

        with patch("sys.stdout"):
            result = self.client.read_sensors()

        self.assertEqual(result["temp"], 24.5)
        self.assertEqual(result["humid"], 60.0)
        self.assertIsNone(result["co2"])
        self.assertEqual(result["light_percent"], 55.5)

    def test_read_sensors_keeps_other_values_when_light_fails(self):
        self.light.get_light_percent.side_effect = RuntimeError("light failed")

        with patch("sys.stdout"):
            result = self.client.read_sensors()

        self.assertEqual(result["temp"], 24.5)
        self.assertEqual(result["humid"], 60.0)
        self.assertEqual(result["co2"], 900)
        self.assertIsNone(result["light_percent"])

    def test_read_sensors_accepts_legacy_dht22_api(self):
        delattr(self.dht22, "get_dht_data_with_status")
        self.dht22.get_dht_data = MagicMock(return_value=(23.0, 58.0))

        result = self.client.read_sensors()

        self.assertEqual(result["temp"], 23.0)
        self.assertEqual(result["humid"], 58.0)

    def test_read_sensors_reports_stale_dht22_value(self):
        self.dht22.get_dht_data_with_status.return_value = (
            24.5,
            60.0,
            "stale",
            "CRC",
        )

        with patch("sys.stdout") as stdout:
            result = self.client.read_sensors()

        self.assertEqual(result["temp"], 24.5)
        self.assertEqual(result["humid"], 60.0)
        stdout.write.assert_called()

    def test_client_test_adds_client_id_to_every_json_line(self):
        socket_instance = MagicMock()
        socket_context = MagicMock()
        socket_context.__enter__.return_value = socket_instance
        socket_context.__exit__.return_value = None
        sensor_data = {
            "temp": 24.5,
            "humid": 60.0,
            "co2": 900,
            "light_percent": 55.5,
        }

        with patch.object(self.client.socket, "socket", return_value=socket_context):
            with patch.object(
                self.client, "read_sensors", return_value=sensor_data.copy()
            ):
                with patch.object(self.client.time, "sleep") as mock_sleep:
                    with patch("sys.stdout"):
                        self.client.client_test("raspi-lab", "127.0.0.1", 8765)

        socket_instance.connect.assert_called_once_with(("127.0.0.1", 8765))
        self.assertEqual(socket_instance.sendall.call_count, self.client.SEND_COUNT)
        self.assertEqual(mock_sleep.call_count, self.client.SEND_COUNT)

        for call_args in socket_instance.sendall.call_args_list:
            payload = call_args.args[0]
            self.assertTrue(payload.endswith(b"\n"))
            decoded = json.loads(payload.decode("utf-8"))
            self.assertEqual(
                decoded,
                {"client_id": "raspi-lab", **sensor_data},
            )


if __name__ == "__main__":
    unittest.main()
