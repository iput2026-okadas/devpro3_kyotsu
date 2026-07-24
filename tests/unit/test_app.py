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

    def _write_csv(
        self,
        name,
        rows,
        columns=("id", "client_id", "timestamp", "temp", "humid"),
    ):
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

    def test_index_selects_latest_csv_by_default(self):
        self._write_csv(
            "data-20260702120000.csv",
            [[1, "raspi-lab", "2026-07-02 12:00:00", 20, 40]],
        )
        self._write_csv(
            "data-20260703120000.csv",
            [
                [1, "raspi-lab", "2026-07-03 12:00:00", 25, 50],
                [2, "raspi-office", "2026-07-03 12:05:00", 26, 52],
            ],
        )

        context = self._get_template_context()

        self.assertEqual(
            context["csv_files"],
            ["data-20260703120000.csv", "data-20260702120000.csv"],
        )
        self.assertEqual(context["selected_file"], "data-20260703120000.csv")
        self.assertEqual(
            context["columns"],
            ["id", "client_id", "timestamp", "temp", "humid"],
        )
        self.assertEqual(context["row_count"], 2)
        self.assertEqual([row["id"] for row in context["rows"]], ["1", "2"])
        self.assertEqual(
            [row["client_id"] for row in context["rows"]],
            ["raspi-lab", "raspi-office"],
        )

    def test_index_loads_selected_csv(self):
        self._write_csv(
            "data-20260702120000.csv",
            [[101, "raspi-lab", "2026-07-02 12:00:00", 22, 45]],
        )
        self._write_csv(
            "data-20260703120000.csv",
            [[201, "raspi-office", "2026-07-03 12:00:00", 25, 50]],
        )

        context = self._get_template_context(
            {"file": "data-20260702120000.csv"},
        )

        self.assertEqual(context["selected_file"], "data-20260702120000.csv")
        self.assertEqual(context["row_count"], 1)
        self.assertEqual(context["rows"][0]["id"], "101")
        self.assertEqual(context["rows"][0]["client_id"], "raspi-lab")

    def test_index_calculates_rounded_averages_and_ignores_invalid_rows(self):
        self._write_csv(
            "data-20260703120000.csv",
            [
                [1, "raspi-lab", "2026-07-03 12:00:00", 10, 40],
                [2, "raspi-office", "2026-07-03 12:05:00", 21, 51],
                [3, "raspi-lab", "2026-07-03 12:10:00", "invalid", "invalid"],
            ],
        )

        context = self._get_template_context()

        self.assertEqual(context["avg_temperature"], 15.5)
        self.assertEqual(context["avg_humidity"], 45.5)

    def test_index_handles_header_only_csv(self):
        self._write_csv("data-20260703120000.csv", [])

        context = self._get_template_context()

        self.assertEqual(
            context["columns"],
            ["id", "client_id", "timestamp", "temp", "humid"],
        )
        self.assertEqual(context["rows"], [])
        self.assertEqual(context["row_count"], 0)
        self.assertEqual(context["avg_temperature"], 0)
        self.assertEqual(context["avg_humidity"], 0)

    def test_index_handles_csv_without_temperature_or_humidity_columns(self):
        self._write_csv(
            "data-20260703120000.csv",
            [[1, "raspi-lab", "2026-07-03 12:00:00"]],
            columns=("id", "client_id", "timestamp"),
        )

        context = self._get_template_context()

        self.assertEqual(context["row_count"], 1)
        self.assertEqual(context["avg_temperature"], 0)
        self.assertEqual(context["avg_humidity"], 0)

    def test_index_remains_compatible_with_csv_without_client_id(self):
        self._write_csv(
            "data-20260703120000.csv",
            [[1, "2026-07-03 12:00:00", 25, 50]],
            columns=("id", "timestamp", "temp", "humid"),
        )

        context = self._get_template_context()

        self.assertEqual(context["columns"], ["id", "timestamp", "temp", "humid"])
        self.assertEqual(context["rows"][0]["temp"], "25")
        self.assertEqual(context["avg_temperature"], 25.0)

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
            writer.writerow(("id", "client_id", "timestamp", "temp", "humid"))
            writer.writerow((999, "raspi-outside", "2026-07-03 12:00:00", 99, 99))

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

    def test_chat_returns_ai_response_for_selected_csv(self):
        self._write_csv(
            "data-20260703120000.csv",
            [[1, "raspi-lab", "2026-07-03 12:00:00", 25, 50]],
        )
        conversation = [{"role": "user", "content": "前の質問"}]

        with patch.object(
            app_module.CHATBOT,
            "chat",
            return_value="温度は安定しています。",
        ) as mock_chat:
            response = self.client.post(
                "/api/chat",
                json={
                    "message": " 現在の状態は？ ",
                    "file": "data-20260703120000.csv",
                    "conversation": conversation,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "response": "温度は安定しています。",
                "selected_file": "data-20260703120000.csv",
            },
        )
        mock_chat.assert_called_once_with(
            "現在の状態は？",
            "data-20260703120000.csv",
            conversation,
        )

    def test_chat_validates_question_and_selected_csv(self):
        empty_response = self.client.post("/api/chat", json={"message": "  "})
        self.assertEqual(empty_response.status_code, 400)

        missing_response = self.client.post(
            "/api/chat",
            json={
                "message": "現在の状態は？",
                "file": "../outside.csv",
            },
        )
        self.assertEqual(missing_response.status_code, 404)

    def test_chat_maps_analysis_and_ollama_errors_to_http_statuses(self):
        self._write_csv(
            "data-20260703120000.csv",
            [[1, "raspi-lab", "2026-07-03 12:00:00", 25, 50]],
        )
        cases = (
            (app_module.CsvDataError("CSV不正"), 422),
            (app_module.OllamaConnectionError("接続不可"), 503),
            (app_module.OllamaResponseError("応答不正"), 502),
        )

        for error, expected_status in cases:
            with self.subTest(error=error):
                with patch.object(
                    app_module.CHATBOT,
                    "chat",
                    side_effect=error,
                ):
                    response = self.client.post(
                        "/api/chat",
                        json={
                            "message": "現在の状態は？",
                            "file": "data-20260703120000.csv",
                        },
                    )

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.get_json()["error"], str(error))


if __name__ == "__main__":
    unittest.main()
