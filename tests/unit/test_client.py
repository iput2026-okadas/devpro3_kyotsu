import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


CLIENT_PATH = Path(__file__).resolve().parents[2] / "Client" / "client.py"


def load_client_module():
    spec = importlib.util.spec_from_file_location("client_under_test", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    sensor_modules = {
        "co2": MagicMock(),
        "dht22": MagicMock(),
        "light": MagicMock(),
    }
    with patch.dict(sys.modules, sensor_modules):
        spec.loader.exec_module(module)
    return module


class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = load_client_module()

    def test_parse_arguments_reads_client_id_host_and_port(self):
        arguments = self.client.parse_arguments(
            ["-i", " raspi-lab ", "-h", "192.0.2.10", "-p", "9000"]
        )

        self.assertEqual(arguments.client_id, "raspi-lab")
        self.assertEqual(arguments.host, "192.0.2.10")
        self.assertEqual(arguments.port, 9000)

        long_option_arguments = self.client.parse_arguments(
            ["--client-id", "raspi-office"]
        )
        self.assertEqual(long_option_arguments.client_id, "raspi-office")

    def test_parse_arguments_requires_non_empty_client_id(self):
        for arguments in ([], ["-i", "   "]):
            with self.subTest(arguments=arguments):
                with patch("sys.stderr", new_callable=io.StringIO):
                    with self.assertRaises(SystemExit):
                        self.client.parse_arguments(arguments)

    def test_client_test_adds_client_id_to_every_json_line(self):
        sensor_data = {
            "temp": 25.5,
            "humid": 60,
            "co2": 1100,
            "light_percent": 48.5,
        }
        socket_context = MagicMock()
        connected_socket = socket_context.__enter__.return_value
        self.client.SEND_COUNT = 2

        with patch.object(
            self.client.socket,
            "socket",
            return_value=socket_context,
        ), patch.object(
            self.client,
            "read_sensors",
            return_value=sensor_data.copy(),
        ):
            with patch.object(self.client.time, "sleep"), patch(
                "sys.stdout",
                new_callable=io.StringIO,
            ):
                self.client.client_test("raspi-lab", "192.0.2.10", 9000)

        connected_socket.connect.assert_called_once_with(("192.0.2.10", 9000))
        self.assertEqual(connected_socket.sendall.call_count, 2)
        for send_call in connected_socket.sendall.call_args_list:
            json_line = send_call.args[0]
            self.assertTrue(json_line.endswith(b"\n"))
            payload = json.loads(json_line.decode("utf-8"))
            self.assertEqual(payload["client_id"], "raspi-lab")
            self.assertEqual(payload["temp"], 25.5)


if __name__ == "__main__":
    unittest.main()
