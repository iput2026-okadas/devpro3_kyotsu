import os

import requests


latest_data = {
    "temp": None,
    "humid": None,
    "co2": None,
    "light_percent": None,
}

current_status = "normal"

# Discord または Slack の Webhook URL を設定します。
# 実際の URL はコミットせず、環境変数 WEBHOOK_URL から読み込む形にします。
WEBHOOK_URL = os.environ.get(
    "WEBHOOK_URL",
    "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE",
)


def send_alert(co2_value, level):
    """Discord/Slack に通知を送る。"""
    if not WEBHOOK_URL or "YOUR_WEBHOOK_URL" in WEBHOOK_URL:
        print("Webhook URLが設定されていません。")
        return

    if level == "warning":
        message = f"⚠️ 【注意】 CO₂濃度が上昇しています! 現在: {co2_value} ppm (1000ppm以上)"
    elif level == "danger":
        message = f"🚨 【警告】 すぐに換気してください! 現在: {co2_value} ppm (1500ppm以上)"
    elif level == "recover":
        message = f"✅ 【回復】 CO₂濃度が正常範囲内(1000ppm未満)です。 現在: {co2_value} ppm"
    else:
        return

    payload = {"content": message}  # Slack の場合は {"text": message}
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"送信完了: {message}")
    except Exception as e:
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
