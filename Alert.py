from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

# 最新のセンサーデータを保持する変数
latest_data = {
    "temperature": 0.0,
    "humidity": 0.0,
    "co2": 0,
    "light": 0
}

# --- 設定：Discord または Slack の Webhook URL ---
# Discord の場合は「チャンネル編集 -> 連携サービス -> ウェブフックを作成」から取得
# Slack の場合は Incoming Webhooks アプリを追加して取得
WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE"

def send_alert(co2_value, level):
    """Discord/Slack に通知を送る関数"""
    if not WEBHOOK_URL or "YOUR_WEBHOOK_URL" in WEBHOOK_URL:
        print("Webhook URLが設定されていません。")
        return

    if level == "warning":
        message = f"⚠️ 【注意】 CO₂濃度が上昇しています! 現在: {co2_value} ppm (1000ppm以上)"
    elif level == "danger":
        message = f"🚨 【警告】 すぐに換気してください! 現在: {co2_value} ppm (1500ppm以上)"
    else:
        return

    payload = {"content": message} # Slackの場合は {"text": message}
    try:
        requests.post(WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"通知送信エラー: {e}")

# ① RasPi から JSON データを受け取るエンドポイント
@app.route('/api/data', methods=['POST'])
def receive_data():
    global latest_data
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    
    # データの更新
    latest_data["temperature"] = data.get("temperature", latest_data["temperature"])
    latest_data["humidity"] = data.get("humidity", latest_data["humidity"])
    latest_data["co2"] = data.get("co2", latest_data["co2"])
    latest_data["light"] = data.get("light", latest_data["light"])
    
    # CO₂ 濃度によるアラート判定
    co2 = latest_data["co2"]
    if co2 >= 1500:
        send_alert(co2, "danger")
    elif co2 >= 1000:
        send_alert(co2, "warning")
        
    return jsonify({"status": "success", "received": latest_data}), 200

# ② スマホ・ブラウザ表示用のHTMLエンドポイント
@app.route('/')
def index():
    # 簡易的なHTML/CSS/JS。3秒ごとに自動更新して最新データを表示
    html_template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ルーム環境モニター</title>
        <style>
            body { font-family: sans-serif; background: #f0f2f5; text-align: center; padding: 20px; }
            .card { background: white; border-radius: 10px; padding: 20px; margin: 10px auto; max-width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .value { font-size: 24px; font-weight: bold; color: #007bff; }
            .alert-warn { background: #fff3cd; color: #856404; }
            .alert-danger { background: #f8d7da; color: #721c24; }
        </style>
        <script>
            // 3秒ごとにページをリロードして最新情報を取得
            setTimeout(() => { location.reload(); }, 3000);
        </script>
    </head>
    <body>
        <h1>📊 ルーム環境モニター</h1>
        
        <div class="card {% if data.co2 >= 1500 %}alert-danger{% elif data.co2 >= 1000 %}alert-warn{% endif %}">
            <h3>CO₂ 濃度</h3>
            <p class="value">{{ data.co2 }} ppm</p>
            {% if data.co2 >= 1500 %}<p><strong>🚨 要換気！</strong></p>
            {% elif data.co2 >= 1000 %}<p><strong>⚠️ 窓を開けましょう</strong></p>{% endif %}
        </div>

        <div class="card">
            <h3>温湿度</h3>
            <p class="value">{{ data.temperature }} °C / {{ data.humidity }} %</p>
        </div>

        <div class="card">
            <h3>光量</h3>
            <p class="value">{{ data.light }}</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, data=latest_data)

if __name__ == '__main__':
    # 外部（RasPiやスマホ）からアクセスできるように 0.0.0.0 で起動
    app.run(host='0.0.0.0', port=5000, debug=True)