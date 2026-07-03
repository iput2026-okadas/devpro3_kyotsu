import unittest
from unittest.mock import patch
import sys
import os

# プロジェクトのルートディレクトリをパスに追加し、Serverモジュールをインポートできるようにする
# (__file__ は test_alert.py、そこから ../../ でプロジェクトルートを指す)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, project_root)

from Server import alert

class TestAlert(unittest.TestCase):
    def setUp(self):
        """
        各テストメソッドの実行前に呼ばれる初期化処理。
        alert.py はグローバル変数を使用しているため、テスト間で状態を引き継がないようにリセットします。
        """
        alert.latest_data = {
            "temp": None,
            "humid": None,
            "co2": None,
            "light_percent": None,
        }
        alert.current_status = "normal"
        
        # 通知処理がスキップされないように、ダミーの有効なWebhook URLをセット
        alert.WEBHOOK_URL = "https://discord.com/api/webhooks/VALID_TEST_URL"

    @patch('Server.alert.requests.post')
    def test_send_alert_warning(self, mock_post):
        """send_alert関数: warningレベルの通知が正しく送信されるか"""
        alert.send_alert(1200, "warning")
        
        # requests.postが1回呼ばれたことを確認
        mock_post.assert_called_once()
        
        # 呼ばれたときの引数（ペイロードの中身）に「注意」が含まれているか確認
        _, kwargs = mock_post.call_args
        self.assertIn("注意", kwargs['json']['content'])

    @patch('Server.alert.requests.post')
    def test_send_alert_danger(self, mock_post):
        """send_alert関数: dangerレベルの通知が正しく送信されるか"""
        alert.send_alert(1600, "danger")
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertIn("警告", kwargs['json']['content'])

    @patch('Server.alert.requests.post')
    def test_process_sensor_data_normal_to_warning(self, mock_post):
        """process_sensor_data関数: normal から warning への状態遷移"""
        result = alert.process_sensor_data({"co2": 1200})
        
        self.assertEqual(alert.current_status, "warning")
        self.assertEqual(result["co2"], 1200)
        mock_post.assert_called_once() # 通知が飛ぶはず

    @patch('Server.alert.requests.post')
    def test_process_sensor_data_warning_to_danger(self, mock_post):
        """process_sensor_data関数: warning から danger への状態遷移"""
        alert.current_status = "warning" # 事前に警告状態にしておく
        
        alert.process_sensor_data({"co2": 1600})
        
        self.assertEqual(alert.current_status, "danger")
        mock_post.assert_called_once()

    @patch('Server.alert.requests.post')
    def test_process_sensor_data_danger_to_recover(self, mock_post):
        """process_sensor_data関数: danger から normal への回復"""
        alert.current_status = "danger"
        
        alert.process_sensor_data({"co2": 800})
        
        self.assertEqual(alert.current_status, "normal")
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertIn("回復", kwargs['json']['content'])

    @patch('Server.alert.requests.post')
    def test_process_sensor_data_invalid_co2(self, mock_post):
        """process_sensor_data関数: CO2値が不正な文字列の場合"""
        alert.process_sensor_data({"co2": "invalid_string"})
        
        # 状態は変化せず、通知も飛ばないことを確認
        self.assertEqual(alert.current_status, "normal")
        mock_post.assert_not_called()

    @patch('Server.alert.requests.post')
    def test_process_sensor_data_status_not_changed(self, mock_post):
        """process_sensor_data関数: 状態が変わらない場合は通知が飛ばないこと"""
        alert.current_status = "warning"
        
        # すでにwarningの状態で、さらにwarningの数値を送る
        alert.process_sensor_data({"co2": 1100})
        
        self.assertEqual(alert.current_status, "warning")
        # 状態が変化していないので通知（requests.post）は呼ばれないはず
        mock_post.assert_not_called()

if __name__ == '__main__':
    unittest.main()