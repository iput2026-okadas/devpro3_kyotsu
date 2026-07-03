import io
import unittest
from unittest.mock import call, patch

import requests

from Server import alert


class TestAlert(unittest.TestCase):
    DUMMY_WEBHOOK_URL = "https://example.invalid/slack-webhook"

    def setUp(self):
        self.original_latest_data = alert.latest_data
        self.original_status = alert.current_status
        self.original_webhook_url = alert.SLACK_WEBHOOK_URL

        alert.latest_data = {
            "temp": None,
            "humid": None,
            "co2": None,
            "light_percent": None,
        }
        alert.current_status = "normal"
        alert.SLACK_WEBHOOK_URL = self.DUMMY_WEBHOOK_URL
        self.addCleanup(self._restore_globals)

    def _restore_globals(self):
        alert.latest_data = self.original_latest_data
        alert.current_status = self.original_status
        alert.SLACK_WEBHOOK_URL = self.original_webhook_url

    @patch("Server.alert.requests.post")
    def test_send_alert_warning(self, mock_post):
        with patch("sys.stdout", new_callable=io.StringIO):
            alert.send_alert(1200, "warning")

        mock_post.assert_called_once_with(
            self.DUMMY_WEBHOOK_URL,
            json={
                "text": "⚠️ 【注意】 CO₂濃度が上昇しています! "
                "現在: 1200 ppm (1000ppm以上)"
            },
            timeout=10,
        )
        mock_post.return_value.raise_for_status.assert_called_once_with()

    @patch("Server.alert.requests.post")
    def test_send_alert_danger_and_recover(self, mock_post):
        cases = (
            (1600, "danger", "警告"),
            (800, "recover", "回復"),
        )

        for co2, level, expected_text in cases:
            with self.subTest(level=level):
                mock_post.reset_mock()
                with patch("sys.stdout", new_callable=io.StringIO):
                    alert.send_alert(co2, level)

                mock_post.assert_called_once()
                _, kwargs = mock_post.call_args
                self.assertEqual(set(kwargs["json"]), {"text"})
                self.assertIn(expected_text, kwargs["json"]["text"])
                self.assertIn(str(co2), kwargs["json"]["text"])
                mock_post.return_value.raise_for_status.assert_called_once_with()

    @patch("Server.alert.requests.post")
    def test_send_alert_without_webhook_url(self, mock_post):
        alert.SLACK_WEBHOOK_URL = None

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            alert.send_alert(1200, "warning")

        self.assertIn("SLACK_WEBHOOK_URLが設定されていません", stdout.getvalue())
        mock_post.assert_not_called()

    @patch("Server.alert.requests.post")
    def test_send_alert_with_unknown_level(self, mock_post):
        alert.send_alert(1200, "unknown")

        mock_post.assert_not_called()

    @patch("Server.alert.requests.post")
    def test_send_alert_handles_request_error(self, mock_post):
        mock_post.side_effect = requests.RequestException("connection failed")

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            alert.send_alert(1200, "warning")

        self.assertIn("通知送信エラー: connection failed", stdout.getvalue())

    @patch("Server.alert.requests.post")
    def test_send_alert_handles_http_error(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = requests.RequestException(
            "bad response"
        )

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            alert.send_alert(1200, "warning")

        self.assertIn("通知送信エラー: bad response", stdout.getvalue())

    @patch("Server.alert.send_alert")
    def test_process_sensor_data_updates_only_received_values(self, mock_send):
        first_result = alert.process_sensor_data({"temp": 25.5, "humid": 60})
        second_result = alert.process_sensor_data({"light_percent": 80})

        self.assertIs(second_result, alert.latest_data)
        self.assertEqual(
            second_result,
            {
                "temp": 25.5,
                "humid": 60,
                "co2": None,
                "light_percent": 80,
            },
        )
        self.assertIs(first_result, second_result)
        mock_send.assert_not_called()

    @patch("Server.alert.send_alert")
    def test_process_sensor_data_co2_boundaries(self, mock_send):
        cases = (
            (999, "normal", None),
            (1000, "warning", "warning"),
            (1499, "warning", "warning"),
            (1500, "danger", "danger"),
        )

        for co2, expected_status, expected_level in cases:
            with self.subTest(co2=co2):
                alert.current_status = "normal"
                alert.latest_data["co2"] = None
                mock_send.reset_mock()

                result = alert.process_sensor_data({"co2": co2})

                self.assertEqual(alert.current_status, expected_status)
                self.assertEqual(result["co2"], co2)
                if expected_level is None:
                    mock_send.assert_not_called()
                else:
                    mock_send.assert_called_once_with(co2, expected_level)

    @patch("Server.alert.send_alert")
    def test_process_sensor_data_state_transitions(self, mock_send):
        alert.process_sensor_data({"co2": 1200})
        alert.process_sensor_data({"co2": 1600})
        alert.process_sensor_data({"co2": 800})

        self.assertEqual(alert.current_status, "normal")
        self.assertEqual(
            mock_send.call_args_list,
            [
                call(1200, "warning"),
                call(1600, "danger"),
                call(800, "recover"),
            ],
        )

    @patch("Server.alert.send_alert")
    def test_process_sensor_data_does_not_repeat_same_status_alert(self, mock_send):
        for status, values in (("warning", (1100, 1499)), ("danger", (1500, 2000))):
            with self.subTest(status=status):
                alert.current_status = status
                mock_send.reset_mock()

                for value in values:
                    alert.process_sensor_data({"co2": value})

                self.assertEqual(alert.current_status, status)
                mock_send.assert_not_called()

    @patch("Server.alert.send_alert")
    def test_process_sensor_data_ignores_none_co2(self, mock_send):
        result = alert.process_sensor_data({"co2": None})

        self.assertEqual(alert.current_status, "normal")
        self.assertIsNone(result["co2"])
        mock_send.assert_not_called()

    @patch("Server.alert.send_alert")
    def test_process_sensor_data_rejects_non_numeric_co2(self, mock_send):
        for value in ("invalid", ""):
            with self.subTest(value=value):
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    result = alert.process_sensor_data({"co2": value})

                self.assertEqual(alert.current_status, "normal")
                self.assertEqual(result["co2"], value)
                self.assertIn(f"CO2値が数値ではありません: {value}", stdout.getvalue())
                mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
