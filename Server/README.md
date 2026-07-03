# サーバー側プログラム

`Server/` には、Raspberry Pi から送られてくるセンサーデータを受信・保存・表示する
ためのプログラムを配置しています。CO2 濃度に応じた Webhook 通知、室内環境の
ルールベース判定とチャットボットのサンプルも含まれています。

## ファイル構成

```text
Server/
  server.py               TCP JSON 受信サーバーと CSV 書き出し処理。
  app.py                  Flask 製の CSV ビューア。
  alert.py                CO2 アラート用の Webhook 通知判定モジュール。
  analyze_environment.py  室内環境の詳細なルールベース判定処理。
  environment_advisor.py  チャットボット用の簡易環境判定処理。
  chatbot.py              環境に関する質問へ応答するクラス。
  chatbot-main.py         固定データを使った環境判定の実行例。
  .env.example            Slack Webhook 設定ファイルのひな形。
  templates/              CSV ビューア用 HTML テンプレート。
  static/                 CSV ビューア用 CSS と JavaScript。
  data/                   CSV の保存先と既存のサンプルデータ。
  requirements.txt        サーバー側プログラムの Python 依存関係。
```

## セットアップ

```bash
cd Server
python -m pip install -r requirements.txt
```

## TCP 受信サーバー

`server.py` は TCP ソケットで JSON データを受信し、メモリ上に保持します。
受信したデータは `alert.py` の `process_sensor_data()` にも渡され、CO2 濃度に応じた
Webhook 通知判定に使われます。

起動例:

```bash
python server.py -h 0.0.0.0 -p 8765
```

`Ctrl+C` で終了すると、受信済みデータを
`data/data-YYYYMMDDHHMMSS.csv` として保存します。現在 CSV に保存する列は `id`,
`timestamp`, `temp`, `humid` です。クライアントから送信される `co2` と
`light_percent` は CSV 保存対象には含まれていません。通知判定に使われるのは
`co2` のみです。

現在の受信処理は、1回の `recv(1024)` で1つの完全な JSON を受信する前提です。
TCP 上でJSONが分割または結合された場合のバッファリング処理は未実装です。

## CSV ビューア

`app.py` は `data/` にある `data-*.csv` を探し、ブラウザで一覧表示します。

起動例:

```bash
python app.py
```

ブラウザで `http://localhost:5001/` を開きます。ファイルの切り替え、列ごとの並べ替え、
平均温度・平均湿度の表示、CSVまたはJSON形式でのエクスポートができます。

## Webhook アラート

`alert.py` は HTTP エンドポイントではなく、`server.py` から呼び出される通知判定
モジュールです。CO2 濃度が 1000 ppm 以上になると注意、1500 ppm 以上になると警告、
1000 ppm 未満へ戻ると回復を通知します。同じ状態が続く間は通知を繰り返しません。

`.env.example` を `.env` へコピーし、Slack Incoming Webhook URL を設定します。

```bash
cp .env.example .env
chmod 600 .env
```

`.env` の内容:

```dotenv
SLACK_WEBHOOK_URL="<slack-incoming-webhook-url>"
```

`.env` は `.gitignore` の対象ですが、暗号化はされないため、実際の URL を
`.env.example` やソースコードへ書き込まず、ファイルの閲覧権限も制限してください。
`alert.py` は `python-dotenv` で `Server/.env` を読み込み、Slack 用の
`{"text": "..."}` を送信します。実行環境に `SLACK_WEBHOOK_URL` が設定済みの場合は、
`.env` より実行環境の値が優先されます。

設定後は TCP サーバーを起動します。

```bash
python server.py -h 0.0.0.0 -p 8765
```

通知判定で扱う JSON は `Client/client.py` が送信する形式と同じです。

```json
{"temp": 24.8, "humid": 60.2, "co2": 1235, "light_percent": 48.5}
```

## 環境判定とチャットボット

`environment_advisor.py` は、気温、湿度、CO2、照度から原因と対策を返す簡易判定処理
です。`chatbot.py` の `EnvironmentChatBot` クラスがこの処理を使用します。

固定のセンサー値を使った実行例:

```bash
python chatbot-main.py
```

`analyze_environment.py` には、低温・低湿度・明るすぎる場合や複合条件も扱う、より
詳細な独立した判定処理があります。現在、チャットボットからは呼び出していません。
