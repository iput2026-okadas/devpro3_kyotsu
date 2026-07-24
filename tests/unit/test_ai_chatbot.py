import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from Server.ai_chatbot import (
    CsvAnalysisChatBot,
    CsvDataError,
    OllamaConnectionError,
    OllamaResponseError,
)


class TestCsvAnalysisChatBot(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name)
        self.bot = CsvAnalysisChatBot(
            self.data_dir,
            model="test-model",
            ollama_url="http://ollama.test/api/chat",
        )

    def _write_csv(self, name, columns, rows):
        path = self.data_dir / name
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(columns)
            writer.writerows(rows)
        return path

    def test_load_rows_accepts_minimum_and_extended_csv_schemas(self):
        self._write_csv(
            "data-minimum.csv",
            ("timestamp", "temp", "humid"),
            (("2026-07-24 10:00:00", 25, 50),),
        )
        minimum_rows = self.bot.load_rows("data-minimum.csv")
        self.assertEqual(minimum_rows[0]["temperature"], 25)
        self.assertIsNone(minimum_rows[0]["co2"])
        self.assertIsNone(minimum_rows[0]["light"])

        self._write_csv(
            "data-extended.csv",
            (
                "client_id",
                "timestamp",
                "temp",
                "humid",
                "co2",
                "light_percent",
            ),
            (
                ("raspi-lab", "2026-07-24 10:00:00", 25, 50, 900, 40),
            ),
        )
        extended_rows = self.bot.load_rows("data-extended.csv")
        self.assertEqual(extended_rows[0]["client_id"], "raspi-lab")
        self.assertEqual(extended_rows[0]["co2"], 900)
        self.assertEqual(extended_rows[0]["light"], 40)

    def test_load_rows_rejects_unsafe_filename_and_missing_columns(self):
        with self.assertRaises(CsvDataError):
            self.bot.load_rows("../data-outside.csv")

        self._write_csv(
            "data-missing.csv",
            ("timestamp", "temp"),
            (("2026-07-24 10:00:00", 25),),
        )
        with self.assertRaisesRegex(CsvDataError, "湿度"):
            self.bot.load_rows("data-missing.csv")

    @patch("Server.ai_chatbot.requests.post")
    def test_chat_sends_csv_summary_and_sanitized_conversation(self, mock_post):
        self._write_csv(
            "data-analysis.csv",
            ("timestamp", "temp", "humid", "co2", "light_percent"),
            (
                ("2026-07-24 10:00:00", 20, 40, 700, 30),
                ("2026-07-24 10:05:00", 24, 50, 900, 50),
            ),
        )
        response = MagicMock(ok=True)
        response.json.return_value = {
            "message": {"content": "温度は4℃上昇しています。"}
        }
        mock_post.return_value = response

        answer = self.bot.chat(
            "変化を教えて",
            "data-analysis.csv",
            conversation=[
                {"role": "user", "content": "前の質問"},
                {"role": "system", "content": "無視される指示"},
                "不正な履歴",
            ],
        )

        self.assertEqual(answer, "温度は4℃上昇しています。")
        request_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(request_json["model"], "test-model")
        self.assertEqual(
            [message["role"] for message in request_json["messages"]],
            ["system", "user", "user"],
        )
        prompt = request_json["messages"][-1]["content"]
        self.assertIn("区間変化 +4.00℃", prompt)
        self.assertIn("CO2: 最新 900.00ppm", prompt)
        self.assertIn("光量: 最新 50.00", prompt)

    @patch("Server.ai_chatbot.requests.post")
    def test_chat_maps_connection_and_invalid_response_errors(self, mock_post):
        self._write_csv(
            "data-analysis.csv",
            ("temp", "humid"),
            ((25, 50),),
        )
        mock_post.side_effect = requests.ConnectionError("offline")
        with self.assertRaises(OllamaConnectionError):
            self.bot.chat("状態は？", "data-analysis.csv")

        invalid_response = MagicMock(ok=True)
        invalid_response.json.return_value = {}
        mock_post.side_effect = None
        mock_post.return_value = invalid_response
        with self.assertRaises(OllamaResponseError):
            self.bot.chat("状態は？", "data-analysis.csv")


if __name__ == "__main__":
    unittest.main()
