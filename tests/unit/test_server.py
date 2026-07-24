import csv
import datetime
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from Server import server

REAL_DATETIME = datetime.datetime


class TestServer(unittest.TestCase):
    def setUp(self):
        self.original_data = server.data
        self.original_data_dir = server.DATA_DIR
        server.data = []
        self.addCleanup(self._restore_globals)

    def _restore_globals(self):
        server.data = self.original_data
        server.DATA_DIR = self.original_data_dir

    @patch("Server.server.dt.datetime")
    def test_add_data_appends_rows_with_sequential_ids(self, mock_datetime):
        mock_datetime.now.return_value = REAL_DATETIME(2026, 7, 3, 12, 34, 56)

        with patch("sys.stdout", new_callable=io.StringIO):
            first_result = server.add_data(
                {"client_id": "raspi-lab", "temp": 25.5, "humid": 60}
            )
            second_result = server.add_data(
                {"client_id": "raspi-office", "temp": 26.0, "humid": 61}
            )

        self.assertTrue(first_result)
        self.assertTrue(second_result)
        self.assertEqual(
            server.data,
            [
                [0, "raspi-lab", "2026-07-03 12:34:56", 25.5, 60],
                [1, "raspi-office", "2026-07-03 12:34:56", 26.0, 61],
            ],
        )

    def test_add_data_skips_missing_or_none_required_fields(self):
        for incomplete_data in (
            {"client_id": "raspi-lab", "humid": 60},
            {"client_id": "raspi-lab", "temp": 25.5},
            {"client_id": "raspi-lab", "temp": None, "humid": 60},
            {"client_id": "raspi-lab", "temp": 25.5, "humid": None},
        ):
            with self.subTest(data=incomplete_data):
                server.data = []

                with patch("sys.stdout", new_callable=io.StringIO):
                    result = server.add_data(incomplete_data)

                self.assertFalse(result)
                self.assertEqual(server.data, [])

    def test_add_data_rejects_missing_client_id(self):
        with self.assertRaises(KeyError):
            server.add_data({"temp": 25.5, "humid": 60})

    def test_add_data_rejects_empty_client_id(self):
        for client_id in ("", "   ", None, 123):
            with self.subTest(client_id=client_id):
                server.data = []

                with self.assertRaises(ValueError):
                    server.add_data(
                        {"client_id": client_id, "temp": 25.5, "humid": 60}
                    )

                self.assertEqual(server.data, [])

    @patch("Server.server.dt.datetime")
    def test_save_data_writes_header_and_rows(self, mock_datetime):
        mock_datetime.now.return_value = REAL_DATETIME(2026, 7, 3, 12, 34, 56)
        server.data = [
            [0, "raspi-lab", "2026-07-03 12:00:00", 25.5, 60],
            [1, "raspi-office", "2026-07-03 12:05:00", 26.0, 61],
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            server.DATA_DIR = Path(temp_dir)
            with patch("sys.stdout", new_callable=io.StringIO):
                server.save_data()

            output_path = Path(temp_dir) / "data-20260703123456.csv"
            self.assertTrue(output_path.exists())
            with output_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(
            rows,
            [
                ["id", "client_id", "timestamp", "temp", "humid"],
                ["0", "raspi-lab", "2026-07-03 12:00:00", "25.5", "60"],
                ["1", "raspi-office", "2026-07-03 12:05:00", "26.0", "61"],
            ],
        )

    @patch("Server.server.dt.datetime")
    def test_save_data_with_no_rows_writes_only_header(self, mock_datetime):
        mock_datetime.now.return_value = REAL_DATETIME(2026, 7, 3, 12, 34, 56)

        with tempfile.TemporaryDirectory() as temp_dir:
            server.DATA_DIR = Path(temp_dir)
            with patch("sys.stdout", new_callable=io.StringIO):
                server.save_data()

            output_path = Path(temp_dir) / "data-20260703123456.csv"
            with output_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(
            rows,
            [["id", "client_id", "timestamp", "temp", "humid"]],
        )

    @patch("Server.server.alert.process_sensor_data")
    @patch("Server.server.add_data")
    def test_recv_data1024_processes_json_until_normal_disconnect(
        self,
        mock_add_data,
        mock_process_sensor_data,
    ):
        sensor_data = {
            "client_id": "raspi-lab",
            "temp": 25.5,
            "humid": 60,
            "co2": 1100,
            "light_percent": 55.5,
        }
        client_socket = MagicMock()
        client_socket.recv.side_effect = [json.dumps(sensor_data).encode("utf-8"), b""]

        with patch("sys.stdout", new_callable=io.StringIO):
            server.recv_data1024(client_socket, ("127.0.0.1", 50000))

        mock_add_data.assert_called_once_with(sensor_data)
        mock_process_sensor_data.assert_called_once_with(sensor_data)
        self.assertEqual(client_socket.recv.call_args_list, [call(1024), call(1024)])
        client_socket.close.assert_called_once_with()

    @patch("Server.server.alert.process_sensor_data")
    @patch("Server.server.add_data")
    def test_recv_data1024_skips_incomplete_data_and_accepts_next_measurement(
        self,
        mock_add_data,
        mock_process_sensor_data,
    ):
        incomplete_data = {
            "client_id": "raspi-lab",
            "temp": None,
            "humid": None,
            "co2": 1100,
            "light_percent": 55.5,
        }
        complete_data = {
            "client_id": "raspi-lab",
            "temp": 25.5,
            "humid": 60,
            "co2": 1100,
            "light_percent": 55.5,
        }
        client_socket = MagicMock()
        client_socket.recv.side_effect = [
            json.dumps(incomplete_data).encode("utf-8"),
            json.dumps(complete_data).encode("utf-8"),
            b"",
        ]

        with patch("sys.stdout", new_callable=io.StringIO):
            server.recv_data1024(client_socket, ("127.0.0.1", 50000))

        mock_add_data.assert_called_once_with(complete_data)
        mock_process_sensor_data.assert_called_once_with(complete_data)
        self.assertEqual(client_socket.recv.call_count, 3)
        client_socket.close.assert_called_once_with()

    def test_recv_data1024_handles_invalid_json_and_closes_socket(self):
        client_socket = MagicMock()
        client_socket.recv.return_value = b"not-json"

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            server.recv_data1024(client_socket, ("127.0.0.1", 50000))

        self.assertIn("エラー:", stdout.getvalue())
        client_socket.close.assert_called_once_with()

    def test_recv_data1024_handles_connection_reset_and_closes_socket(self):
        client_socket = MagicMock()
        client_socket.recv.side_effect = ConnectionResetError

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            server.recv_data1024(client_socket, ("127.0.0.1", 50000))

        self.assertIn("強制切断: ('127.0.0.1', 50000)", stdout.getvalue())
        client_socket.close.assert_called_once_with()

    def test_recv_data1024_handles_unexpected_error_and_closes_socket(self):
        client_socket = MagicMock()
        client_socket.recv.side_effect = OSError("receive failed")

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            server.recv_data1024(client_socket, ("127.0.0.1", 50000))

        self.assertIn("エラー: receive failed", stdout.getvalue())
        client_socket.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
