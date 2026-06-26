# IoT 環境モニタリングシステム

Raspberry Pi で取得した室内環境データを PC 側の TCP サーバーへ送信し、
受信したデータを CSV として保存・表示するための小規模な IoT
モニタリングシステムです。

クライアント側は温度、湿度、CO2 濃度、光量を読み取り、JSON 形式で送信します。
サーバー側は TCP ソケットで JSON を受信し、プロセス終了時に CSV ファイルへ
書き出します。サーバー側には、CSV 表示用の Flask アプリ、CO2 濃度に応じた
Webhook アラート、気温変化の原因を分類する機械学習デモも含まれています。

注意: サーバー側ディレクトリ名は `Server/` ではなく、現状のリポジトリに合わせて
`Sever/` です。

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
├── Sever/
│   ├── server.py
│   ├── app-new.py
│   ├── alert.py
│   ├── detective.py
│   ├── data/
│   ├── static/
│   ├── templates/
│   ├── requirements.txt
│   └── README.md
├── tests/
│   └── README.md
└── README.md
```

## 使用方法

### 1. サーバー側を起動する

PC 側で TCP 受信サーバーを起動します。

```bash
cd Sever
python -m pip install -r requirements.txt
python server.py -h 0.0.0.0 -p 8765
```

サーバーを `Ctrl+C` で終了すると、それまでに受信したデータが
`Sever/data-YYYYMMDDHHMMSS.csv` として保存されます。

### 2. クライアント側を起動する

Raspberry Pi 側で依存関係をインストールし、PC 側サーバーの IP アドレスを指定して
クライアントを起動します。

```bash
cd Client
python -m pip install -r requirements.txt
sudo python client.py -h <server-ip-address> -p 8765
```

送信される JSON は次の形式です。

```json
{"temp": 24.8, "humid": 60.2, "co2": 1235, "light_percent": 48.5}
```

### 3. CSV ビューアを起動する

保存された `Sever/data-*.csv` をブラウザで確認する場合は、Flask アプリを起動します。

```bash
cd Sever
python app-new.py
```

ブラウザで `http://localhost:5001/` を開くと、CSV の一覧と内容を確認できます。

### 4. Webhook アラートを起動する

CO2 濃度に応じた Discord または Slack 通知を確認する場合は、`Sever/alert.py` の
Webhook URL を環境に合わせて設定してから起動します。実際の Webhook URL は
コミットしないでください。

```bash
cd Sever
python alert.py
```

この Flask アプリは `POST /api/data` で次の JSON を受け取ります。

```json
{"temperature": 24.8, "humidity": 60.2, "co2": 1235, "light": 48.5}
```

## 検証

構文確認には次のコマンドを使います。

```bash
python -m py_compile Client/client.py Client/co2.py Client/dht22.py Client/light.py Client/light_mcp3008.py Sever/server.py Sever/alert.py Sever/detective.py Sever/app-new.py
```

テスト方針は `tests/README.md` にまとめています。Python の単体テストは
`unittest`、ブラウザ E2E テストは Playwright を使う方針です。
