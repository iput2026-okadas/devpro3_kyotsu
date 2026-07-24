# IoT 環境モニタリングシステム

Raspberry Pi で取得した室内環境データを PC 側の TCP サーバーへ送信し、
受信したデータを CSV として保存・表示するための小規模な IoT
モニタリングシステムです。

クライアント側は自身のクライアントIDと、温度、湿度、CO2 濃度、光量を読み取り、
JSON 形式で送信します。
サーバー側は TCP ソケットで JSON を受信してメモリ上に保持し、プロセスを
`Ctrl+C` で終了したときに CSV ファイルへ書き出します。受信データは通知判定
モジュールにも渡され、CO2 濃度に応じて Slack Incoming Webhook へ通知できます。

サーバー側には、CSV 表示用の Flask アプリ、センサー値から室内環境の原因と対策を
返す判定処理とチャットボットのサンプルも含まれています。

注意: 現在のサーバー側ディレクトリ名は `Server/` です。

## ディレクトリ構成

```text
.
├── Client/
│   ├── client.py
│   ├── co2.py
│   ├── dht22.py
│   ├── dht22_takemoto.py
│   ├── light.py
│   ├── light_mcp3008.py
│   ├── requirements.txt
│   └── README.md
├── Server/
│   ├── server.py
│   ├── app.py
│   ├── ai_chatbot.py
│   ├── alert.py
│   ├── analyze_environment.py
│   ├── environment_advisor.py
│   ├── chatbot.py
│   ├── chatbot-main.py
│   ├── .env.example
│   ├── data/
│   ├── static/
│   ├── templates/
│   ├── requirements.txt
│   └── README.md
├── tests/
│   ├── unit/
│   ├── e2e/
│   ├── fixtures/
│   ├── requirements.txt
│   └── README.md
├── docs/
│   ├── ai-chat.md
│   ├── test-e2e-scenario.md
│   └── test-unit-scenario.md
└── README.md
```

## 使用方法

### 1. サーバー側を起動する

PC 側で依存関係をインストールし、TCP 受信サーバーを起動します。

```bash
cd Server
python -m pip install -r requirements.txt
python server.py -h 0.0.0.0 -p 8765
```

サーバーを `Ctrl+C` で終了すると、それまでに受信したデータが
`Server/data/data-YYYYMMDDHHMMSS.csv` として保存されます。現在 CSV に保存される
列は `id`, `client_id`, `timestamp`, `temp`, `humid` です。`id` は受信順の連番、
`client_id` は Raspberry Pi の識別名です。クライアントから送信される `co2` と
`light_percent` は CSV には保存されません。通知判定に使われるのは `co2` のみです。

### 2. クライアント側を起動する

Raspberry Pi 側で依存関係をインストールし、PC 側サーバーの IP アドレスを指定して
クライアントを起動します。

```bash
cd Client
python -m pip install -r requirements.txt
sudo python client.py -i <client-id> -h <server-ip-address> -p 8765
```

光量センサーの読み取りには `spidev` も必要です。`spidev` は現在
`Client/requirements.txt` に含まれていないため、Raspberry Pi 側の環境へ別途
インストールしてください。

送信される JSON は次の形式です。

```json
{"client_id": "raspi-lab", "temp": 24.8, "humid": 60.2, "co2": 1235, "light_percent": 48.5}
```

`-i`（`--client-id`）は必須です。Raspberry Pi ごとに重複しない名前を指定して
ください。クライアントはこの JSON の末尾に改行を付け、5秒間隔で6回送信します。

### 3. CSV ビューアを起動する

`Server/data/` に保存された `data-*.csv` をブラウザで確認する場合は、Flask アプリを
起動します。

```bash
cd Server
python app.py
```

ブラウザで `http://localhost:5001/` を開くと、CSV の一覧、内容、平均温度、平均湿度を
確認できます。列の並べ替えと CSV・JSON エクスポートにも対応しています。
右下の「AI分析」では、ローカルOllamaを使って選択中CSVへ質問できます。セットアップ、
対応CSV列、API仕様、テスト方法は `docs/ai-chat.md` を参照してください。

### 4. Webhook アラートを設定する

CO2 濃度に応じた Slack 通知を使う場合は、`.env.example` を `.env` へコピーし、
Slack Incoming Webhook URL を設定します。

```bash
cd Server
cp .env.example .env
chmod 600 .env
```

`Server/.env`:

```dotenv
SLACK_WEBHOOK_URL="<slack-incoming-webhook-url>"
```

`.env` は `.gitignore` の対象ですが、暗号化はされないため、実際の URL を
`.env.example` やソースコードへ書き込まず、ファイルの閲覧権限も制限してください。
設定後は通常どおりサーバーを起動します。

```bash
python server.py -h 0.0.0.0 -p 8765
```

`Server/server.py` が TCP で受信したデータを `Server/alert.py` の
`process_sensor_data()` へ渡します。CO2 濃度が 1000 ppm 以上になると注意、
1500 ppm 以上になると警告、1000 ppm 未満へ戻ると回復を通知します。

`Server/alert.py` は起動時に `python-dotenv` を使って `Server/.env` を読み込み、
`SLACK_WEBHOOK_URL` へ Slack 用の `{"text": "..."}` を送信します。実行環境に同名の
環境変数が設定されている場合は、`.env` より実行環境の値が優先されます。

### 5. 環境判定とチャットボットのサンプルを実行する

固定のセンサー値を環境判定へ渡し、原因と対策を表示するサンプルです。

```bash
cd Server
python chatbot-main.py
```

`chatbot.py` の `EnvironmentChatBot` クラスは、気温、湿度、CO2、照度、原因、対策に
関する簡単な質問へルールベースで応答します。チャットボットは
`environment_advisor.py` の判定処理を使用します。`analyze_environment.py` には、
低温・低湿度・複合条件なども扱う、より詳細な独立した判定処理があります。

## 現在の制約

- TCP はメッセージ境界を保証しませんが、現在の `Server/server.py` は1回の
  `recv(1024)` で1つの完全な JSON を受信する前提です。JSON が分割または結合された
  場合のバッファリング処理は未実装です。
- CSV の保存対象は温度と湿度のみです。CO2 と光量は保存されません。
- Raspberry Pi の GPIO、SPI、シリアル通信を使う処理は実機での確認が必要です。

## 検証

構文確認には次のコマンドを使います。

```bash
python -m py_compile Client/client.py Client/co2.py Client/dht22.py Client/dht22_takemoto.py Client/light.py Client/light_mcp3008.py Server/server.py Server/alert.py Server/app.py Server/ai_chatbot.py Server/analyze_environment.py Server/environment_advisor.py Server/chatbot.py Server/chatbot-main.py
```

テスト方針は `tests/README.md` にまとめています。Python の単体テストは
`unittest`、ブラウザ E2E テストは Playwright を使います。

```bash
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests/unit -p "test_*.py"
python -m playwright install chromium
python -m pytest tests/e2e
```

Unit Test のシナリオは `docs/test-unit-scenario.md`、E2E テストのシナリオは
`docs/test-e2e-scenario.md` を参照してください。
