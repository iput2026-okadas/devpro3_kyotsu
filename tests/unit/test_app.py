import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Server import app as app_module


class TestApp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.temp_root = Path(self.temp_dir.name)
        self.data_dir = self.temp_root / "data"
        self.data_dir.mkdir()

        self.data_dir_patcher = patch.object(app_module, "DATA_DIR", self.data_dir)
        self.data_dir_patcher.start()
        self.addCleanup(self.data_dir_patcher.stop)

        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def _write_csv(self, name, rows, columns=("id", "timestamp", "temp", "humid")):
        path = self.data_dir / name
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(columns)
            writer.writerows(rows)
        return path

    def _get_template_context(self, query_string=None):
        with patch("Server.app.render_template", return_value="rendered") as mock_render:
            response = self.client.get("/", query_string=query_string)

        self.assertEqual(response.status_code, 200)
        mock_render.assert_called_once()
        return mock_render.call_args.kwargs

    def _read_csv(self, path):
        with path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            return list(reader.fieldnames or []), list(reader)

    def test_index_selects_latest_csv_by_default(self):
        self._write_csv(
            "data-20260702120000.csv",
            [[1, "2026-07-02 12:00:00", 20, 40]],
        )
        self._write_csv(
            "data-20260703120000.csv",
            [
                [1, "2026-07-03 12:00:00", 25, 50],
                [2, "2026-07-03 12:05:00", 26, 52],
            ],
        )

        context = self._get_template_context()

        self.assertEqual(
            context["csv_files"],
            ["data-20260703120000.csv", "data-20260702120000.csv"],
        )
        self.assertEqual(context["selected_file"], "data-20260703120000.csv")
        self.assertEqual(context["columns"], ["id", "timestamp", "temp", "humid"])
        self.assertEqual(context["row_count"], 2)
        self.assertEqual([row["id"] for row in context["rows"]], ["1", "2"])
        self.assertEqual(context["client_id_column"], "id")
        self.assertEqual(context["client_ids"], ["1", "2"])

    def test_index_loads_selected_csv(self):
        self._write_csv(
            "data-20260702120000.csv",
            [[101, "2026-07-02 12:00:00", 22, 45]],
        )
        self._write_csv(
            "data-20260703120000.csv",
            [[201, "2026-07-03 12:00:00", 25, 50]],
        )

        context = self._get_template_context(
            {"file": "data-20260702120000.csv"},
        )

        self.assertEqual(context["selected_file"], "data-20260702120000.csv")
        self.assertEqual(context["row_count"], 1)
        self.assertEqual(context["rows"][0]["id"], "101")

    def test_index_calculates_rounded_averages_and_ignores_invalid_rows(self):
        self._write_csv(
            "data-20260703120000.csv",
            [
                [1, "2026-07-03 12:00:00", 10, 40],
                [2, "2026-07-03 12:05:00", 21, 51],
                [3, "2026-07-03 12:10:00", "invalid", "invalid"],
            ],
        )

        context = self._get_template_context()

        self.assertEqual(context["avg_temperature"], 15.5)
        self.assertEqual(context["avg_humidity"], 45.5)

    def test_index_handles_header_only_csv(self):
        self._write_csv("data-20260703120000.csv", [])

        context = self._get_template_context()

        self.assertEqual(context["columns"], ["id", "timestamp", "temp", "humid"])
        self.assertEqual(context["rows"], [])
        self.assertEqual(context["row_count"], 0)
        self.assertEqual(context["avg_temperature"], 0)
        self.assertEqual(context["avg_humidity"], 0)

    def test_index_handles_csv_without_temperature_or_humidity_columns(self):
        self._write_csv(
            "data-20260703120000.csv",
            [[1, "2026-07-03 12:00:00"]],
            columns=("id", "timestamp"),
        )

        context = self._get_template_context()

        self.assertEqual(context["row_count"], 1)
        self.assertEqual(context["avg_temperature"], 0)
        self.assertEqual(context["avg_humidity"], 0)

    def test_index_reports_missing_csv(self):
        context = self._get_template_context({"file": "data-missing.csv"})

        self.assertEqual(context["error"], "data-missing.csv が見つかりません")
        self.assertEqual(context["columns"], [])
        self.assertEqual(context["rows"], [])
        self.assertEqual(context["row_count"], 0)

    def test_index_rejects_paths_outside_data_directory(self):
        outside_file = self.temp_root / "data-outside.csv"
        with outside_file.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(("id", "timestamp", "temp", "humid"))
            writer.writerow((999, "2026-07-03 12:00:00", 99, 99))

        for requested_file in ("../data-outside.csv", str(outside_file.resolve())):
            with self.subTest(file=requested_file):
                context = self._get_template_context({"file": requested_file})

                self.assertIsNotNone(context["error"])
                self.assertEqual(context["columns"], [])
                self.assertEqual(context["rows"], [])

    def test_index_handles_empty_data_directory(self):
        context = self._get_template_context()

        self.assertEqual(context["csv_files"], [])
        self.assertIsNone(context["selected_file"])
        self.assertEqual(context["columns"], [])
        self.assertEqual(context["rows"], [])
        self.assertEqual(context["row_count"], 0)
        self.assertIsNone(context["error"])
        self.assertEqual(context["avg_temperature"], 0)
        self.assertEqual(context["avg_humidity"], 0)
        self.assertIsNone(context["client_id_column"])
        self.assertEqual(context["client_ids"], [])

    def test_add_csv_data_inserts_by_timestamp_and_extends_legacy_columns(self):
        csv_path = self._write_csv(
            "data-20260703120000.csv",
            [
                [101, "2026-07-03 12:00:00", 22.0, 45.0],
                [102, "2026-07-03 12:10:00", 24.0, 47.0],
            ],
        )

        response = self.client.post(
            "/api/data",
            json={
                "file": csv_path.name,
                "client_id": "101",
                "timestamp": "2026-07-03T12:05:30",
                "temp": "23.1",
                "humid": "46.2",
                "co2": "850",
                "light_percent": "48.5",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["inserted_index"], 1)

        columns, rows = self._read_csv(csv_path)
        self.assertEqual(
            columns,
            ["id", "timestamp", "temp", "humid", "co2", "light_percent"],
        )
        self.assertEqual(
            [row["timestamp"] for row in rows],
            [
                "2026-07-03 12:00:00",
                "2026-07-03 12:05:30",
                "2026-07-03 12:10:00",
            ],
        )
        self.assertEqual(rows[1]["id"], "101")
        self.assertEqual(rows[1]["temp"], "23.1")
        self.assertEqual(rows[1]["humid"], "46.2")
        self.assertEqual(rows[1]["co2"], "850")
        self.assertEqual(rows[1]["light_percent"], "48.5")
        self.assertEqual(rows[0]["co2"], "")
        self.assertEqual(rows[2]["light_percent"], "")

    def test_add_csv_data_uses_client_id_column_and_sorts_existing_rows(self):
        columns = (
            "client-id",
            "timestamp",
            "temp",
            "humid",
            "co2",
            "light_percent",
        )
        csv_path = self._write_csv(
            "data-20260703120000.csv",
            [
                ["room-a", "2026-07-03 12:10:00", 24, 47, 900, 50],
                ["room-b", "2026-07-03 12:00:00", 22, 45, 800, 40],
            ],
            columns=columns,
        )

        response = self.client.post(
            "/api/data",
            json={
                "file": csv_path.name,
                "client_id": "room-a",
                "timestamp": "2026-07-03T12:05:00",
                "temp": 23,
                "humid": 46,
                "co2": 850,
                "light_percent": 45,
            },
        )

        self.assertEqual(response.status_code, 201)
        _, rows = self._read_csv(csv_path)
        self.assertEqual(
            [row["client-id"] for row in rows],
            ["room-b", "room-a", "room-a"],
        )

    def test_add_csv_data_rejects_unknown_client_id_without_changing_file(self):
        csv_path = self._write_csv(
            "data-20260703120000.csv",
            [[101, "2026-07-03 12:00:00", 22, 45]],
        )
        original_text = csv_path.read_text(encoding="utf-8")

        response = self.client.post(
            "/api/data",
            json={
                "file": csv_path.name,
                "client_id": "999",
                "timestamp": "2026-07-03T12:05:00",
                "temp": 23,
                "humid": 46,
                "co2": 850,
                "light_percent": 45,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("client-id", response.get_json()["error"])
        self.assertEqual(csv_path.read_text(encoding="utf-8"), original_text)

    def test_add_csv_data_validates_timestamp_and_sensor_ranges(self):
        csv_path = self._write_csv(
            "data-20260703120000.csv",
            [[101, "2026-07-03 12:00:00", 22, 45]],
        )
        valid_payload = {
            "file": csv_path.name,
            "client_id": "101",
            "timestamp": "2026-07-03T12:05:00",
            "temp": 23,
            "humid": 46,
            "co2": 850,
            "light_percent": 45,
        }

        invalid_values = (
            ("timestamp", "2026-07-03T12:05"),
            ("temp", "not-a-number"),
            ("humid", 101),
            ("co2", -1),
            ("light_percent", -0.1),
        )
        for field, value in invalid_values:
            with self.subTest(field=field):
                payload = {**valid_payload, field: value}
                response = self.client.post("/api/data", json=payload)
                self.assertEqual(response.status_code, 400)

        _, rows = self._read_csv(csv_path)
        self.assertEqual(len(rows), 1)

    def test_add_csv_data_rejects_file_outside_data_directory(self):
        response = self.client.post(
            "/api/data",
            json={
                "file": "../data-outside.csv",
                "client_id": "101",
                "timestamp": "2026-07-03T12:05:00",
                "temp": 23,
                "humid": 46,
                "co2": 850,
                "light_percent": 45,
            },
        )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
