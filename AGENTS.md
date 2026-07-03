# AGENTS.md

## プロジェクト概要

このリポジトリは、`Client/` と `Server/` に分かれた小規模な IoT
モニタリングシステムです。

- `Client/` は Raspberry Pi 上で動作し、温度、湿度、CO2 濃度、光量を取得します。
- クライアントは取得したセンサーデータを JSON 行として TCP ソケットへ送信します。
- `Server/` は JSON データを受信し、温度と湿度をメモリ上に保持します。
- TCP サーバープロセスを `Ctrl+C` で終了すると、受信済みデータを CSV へ保存します。
- 受信データは CO2 通知判定にも渡され、Slack Incoming Webhook へ通知できます。
- `Server/` には Flask 製の CSV ビューア、室内環境のルールベース判定、簡易
  チャットボットも含まれています。
- Python の Unit Test と、Playwright を使った CSV ビューアの E2E テストがあります。

注意: 現在のサーバー側ディレクトリ名は `Server/` です。`Sever/` ではありません。
ユーザーから明示的に依頼されない限り、ディレクトリ名を変更しないでください。

## リポジトリ構成

```text
Client/
  client.py            センサーを読み取り、TCP サーバーへ JSON 行を送信する。
  dht22.py             GPIO 26 を使う DHT22 ラッパー。
  dht22_takemoto.py    lgpio を使う DHT22 実装。
  co2.py               /dev/serial0 を使う MH-Z19 系 CO2 センサー読み取り。
  light.py             光量センサー用ラッパー。
  light_mcp3008.py     MCP3008 SPI ADC 読み取り。
  requirements.txt     lgpio と pyserial の依存関係。
  README.md            クライアントのセットアップと実行方法。

Server/
  server.py               TCP JSON 受信サーバーと CSV 書き出し処理。
  app.py                  Flask 製の CSV ビューア。
  alert.py                CO2 状態判定と Slack Webhook 通知処理。
  analyze_environment.py  詳細な室内環境判定処理。
  environment_advisor.py  チャットボット用の簡易環境判定処理。
  chatbot.py              環境に関する質問へ応答するクラス。
  chatbot-main.py         固定データを使った環境判定の実行例。
  .env.example            Slack Webhook 設定のひな形。
  templates/              CSV ビューア用 HTML テンプレート。
  static/                 CSV ビューア用 CSS と JavaScript。
  data/                   CSV の保存先とサンプルデータ。
  requirements.txt        サーバー側の Python 依存関係。
  README.md               サーバー側プログラムの説明と実行方法。

tests/
  unit/                  unittest による alert、server、app の Unit Test。
  e2e/                   Playwright による CSV ビューアの E2E テスト。
  fixtures/csv_viewer/   E2E テスト専用の CSV データ。
  requirements.txt       Unit Test と E2E テストの依存関係。
  README.md              テスト方針と実行方法。

docs/
  test-unit-scenario.md  Unit Test のシナリオ。
  test-e2e-scenario.md   E2E テストのシナリオ。
```

## 実行時の注意点

- `Client/client.py` が送信する JSON キーは `temp`, `humid`, `co2`,
  `light_percent` です。
- クライアントは JSON の末尾に改行を付け、5秒間隔で6回送信します。
- `Server/server.py` が CSV に保存する列は `id`, `timestamp`, `temp`, `humid`
  のみです。`co2` と `light_percent` は CSV には保存されません。
- `Server/alert.py` はクライアントと同じ JSON 形式を受け取り、CO2 値だけを通知判定に
  使用します。1000 ppm 以上は注意、1500 ppm 以上は警告、1000 ppm 未満へ戻ると
  回復を通知します。同じ状態が続く間は通知を繰り返しません。
- `alert.py` は HTTP エンドポイントや単独起動する Flask アプリではありません。
  `server.py` の TCP 受信処理から `process_sensor_data()` が呼び出されます。
- Slack Incoming Webhook URL は `Server/.env` または実行環境の
  `SLACK_WEBHOOK_URL` から読み込みます。実際の URL はコミットしないでください。
- `Server/app.py` は `Server/data/data-*.csv` を読み込みます。ファイル一覧、内容、
  平均温度、平均湿度を表示し、並べ替えと CSV・JSON エクスポートを提供します。
- 現在の TCP 受信処理は、1回の `recv(1024)` で1つの完全な JSON を受信する前提です。
  分割または結合された JSON を処理するバッファリングは未実装です。
- 光量取得に必要な `spidev` は `Client/requirements.txt` に含まれていません。
  Raspberry Pi 側の環境へ別途インストールしてください。

## よく使うコマンド

Raspberry Pi 側のクライアント環境を準備する場合:

```bash
cd Client
python -m pip install -r requirements.txt
```

TCP クライアントを起動する場合:

```bash
cd Client
sudo python client.py -h <server-ip-address> -p 8765
```

サーバー側の環境を準備する場合:

```bash
cd Server
python -m pip install -r requirements.txt
```

TCP 受信サーバーを起動する場合:

```bash
cd Server
python server.py -h 0.0.0.0 -p 8765
```

CSV ビューアを起動する場合:

```bash
cd Server
python app.py
```

ブラウザでは `http://localhost:5001/` を開きます。

Slack 通知を設定する場合:

```bash
cd Server
cp .env.example .env
chmod 600 .env
```

`Server/.env` に次の値を設定した後、TCP サーバーを起動してください。

```dotenv
SLACK_WEBHOOK_URL="<slack-incoming-webhook-url>"
```

固定データを使った環境判定例を実行する場合:

```bash
cd Server
python chatbot-main.py
```

## 検証方法

構文確認:

```bash
python -m py_compile Client/client.py Client/co2.py Client/dht22.py Client/dht22_takemoto.py Client/light.py Client/light_mcp3008.py Server/server.py Server/alert.py Server/app.py Server/analyze_environment.py Server/environment_advisor.py Server/chatbot.py Server/chatbot-main.py
```

Unit Test:

```bash
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests/unit -p "test_*.py"
```

CSV ビューアの E2E テスト:

```bash
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python -m pytest tests/e2e
```

ブラウザ画面を見ながら E2E テストを実行する場合:

```bash
E2E_HEADLESS=false E2E_SLOW_MO=500 python -m pytest tests/e2e -s
```

テストの詳細は `tests/README.md`、シナリオは `docs/test-unit-scenario.md` と
`docs/test-e2e-scenario.md` を参照してください。

## 開発方針

- 変更は小さく保ち、既存のシンプルな Python スクリプト構成に合わせてください。
- 日本語を含むファイルでは UTF-8 を使用してください。
- タスクで別指定がない限り、Raspberry Pi のハードウェア前提を維持してください。
  - DHT22 は GPIO 26 を使用します。
  - CO2 センサーは `/dev/serial0` を使用します。
  - 光量センサーは SPI bus 0、device 0、channel 0 の MCP3008 経由で読み取ります。
- ハードウェアを利用できない環境では、GPIO、SPI、シリアル通信の挙動を明確な理由なく
  変更しないでください。ハードウェアアクセスはモックしやすい小さな関数へ分けます。
- JSON スキーマを変更する場合は、クライアント、TCP 受信サーバー、通知判定の影響を
  一緒に確認してください。
- CSV の列や保存場所を変更する場合は、CSV 書き出し、CSV ビューア、Unit Test、
  E2E テストを一緒に更新してください。
- `Server/data/*.csv` はサンプルデータとして扱い、明示的な依頼がない限り上書きや
  削除をしないでください。テストでは一時ディレクトリと専用 fixture を使用します。
- Slack Webhook の実通信は Unit Test で行わず、`requests.post` をモックしてください。
- `.env`、Webhook URL、その他の秘密情報をコミットしないでください。
- 重いフレームワークの追加は避けてください。このプロジェクトは素の Python
  スクリプト、Flask、unittest、Playwright を中心に構成されています。
