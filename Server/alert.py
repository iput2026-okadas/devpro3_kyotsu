import os
from pathlib import Path

import requests
from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)


latest_data = {
    "temp": None,
    "humid": None,
    "co2": None,
    "light_percent": None,
}

current_status = "normal"

# 実際の URL はコミットせず、Server/.env または実行環境から読み込みます。
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def send_alert(co2_value, level):
    """Slack Incoming Webhook に通知を送る。"""
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URLが設定されていません。")
        return

    if level == "warning":
        message = f"⚠️ 【注意】 CO₂濃度が上昇しています! 現在: {co2_value} ppm (1000ppm以上)"
    elif level == "danger":
        message = f"🚨 【警告】 すぐに換気してください! 現在: {co2_value} ppm (1500ppm以上)"
    elif level == "recover":
        message = f"✅ 【回復】 CO₂濃度が正常範囲内(1000ppm未満)です。 現在: {co2_value} ppm"
    else:
        return

    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"送信完了: {message}")
    except requests.RequestException as e:
        print(f"通知送信エラー: {e}")


def process_sensor_data(sensor_data):
    """client.py と同じ JSON 形式のセンサーデータを受け取り、必要なら通知する。"""
    global current_status

    for key in latest_data:
        if key in sensor_data:
            latest_data[key] = sensor_data[key]

    co2 = latest_data["co2"]
    if co2 is None:
        return latest_data

    try:
        co2_value = float(co2)
    except (TypeError, ValueError):
        print(f"CO2値が数値ではありません: {co2}")
        return latest_data

    if co2_value >= 1500:
        if current_status != "danger":
            current_status = "danger"
            send_alert(co2, "danger")
    elif co2_value >= 1000:
        if current_status != "warning":
            current_status = "warning"
            send_alert(co2, "warning")
    else:
        if current_status != "normal":
            current_status = "normal"
            send_alert(co2, "recover")

    return latest_data
