# AGENTS.md

## プロジェクト概要

このリポジトリは、`Client/` と `Sever/` に分かれた小規模な IoT
モニタリングシステムです。

- `Client/` は Raspberry Pi 上で動作し、各種センサー値を取得します。
- クライアントは取得したセンサーデータを JSON 形式で TCP ソケットへ送信します。
- `Sever/` は JSON データを受信し、受信値をメモリ上に保持します。
- TCP サーバープロセスを中断したタイミングで、それまで受信したデータを CSV
  ファイルへ書き出します。
- `Sever/` には、CSV 表示用の Flask アプリ、Discord または Slack の
  Webhook を使った換気アラート通知プログラム、気温変化の原因を分類する
  機械学習デモも含まれています。

注意: サーバー側ディレクトリ名は現状 `Server` ではなく `Sever` です。
ユーザーから明示的に依頼されない限り、この綴りを変更しないでください。

## リポジトリ構成

```text
Client/
  client.py            TCP クライアント。センサーを読み取り JSON 行を送信する。
  dht22.py             GPIO 26 を使う DHT22 ラッパー。
  dht22_takemoto.py    lgpio を使う DHT22 実装。
  co2.py               /dev/serial0 を使う MH-Z19 系 CO2 センサー読み取り。
  light.py             光量センサー用ラッパー。
  light_mcp3008.py     MCP3008 SPI ADC 読み取り。
  requirements.txt     Raspberry Pi ハードウェア用のクライアント依存関係。

Sever/
  server.py            TCP JSON 受信サーバーと CSV 書き出し処理。
  app-new.py           Flask 製の CSV ビューア。
  alert.py             CO2 アラート用 Flask エンドポイントと Webhook 通知処理。
  detective.py         気温変化原因分類の決定木デモ。
  templates/           CSV ビューア用 HTML テンプレート。
  static/              CSV ビューア用 CSS と JavaScript。
  data/                既存の CSV サンプル。
  requirements.txt     サーバー側データ分析用の依存関係。
```

## 実行時の注意点

- `Client/client.py` が現在送信する JSON キーは `temp`, `humid`, `co2`,
  `light_percent` です。
- `Sever/server.py` が現在 CSV に保存する列は `id`, `timestamp`, `temp`,
  `humid` のみです。
- `Sever/alert.py` は HTTP JSON キーとして `temperature`, `humidity`,
  `co2`, `light` を期待します。これは `server.py` の TCP 受信フローとは別系統です。
- CSV サンプルファイルは `Sever/data/` にあります。一方で `app-new.py` は現在、
  `Sever/` 直下の `data-*.csv` を探す実装になっています。CSV ビューアの挙動を
  変更する前に、意図した CSV 配置を確認してください。
- Discord や Slack の実 Webhook URL はコミットしないでください。設定を追加する場合は、
  プレースホルダーを維持するか、環境変数から読み込む形にしてください。

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
cd Sever
python -m pip install -r requirements.txt
```

TCP 受信サーバーを起動する場合:

```bash
cd Sever
python server.py -h 0.0.0.0 -p 8765
```

CSV ビューアを起動する場合:

```bash
cd Sever
python app-new.py
```

Webhook アラート用 Flask アプリを起動する場合:

```bash
cd Sever
python alert.py
```

気温変化原因分類デモを実行する場合:

```bash
cd Sever
python detective.py
```

## 検証方法

このリポジトリには、現時点で正式なテストスイートはありません。構文確認には次の
コマンドを使ってください。

```bash
python -m py_compile Client/client.py Client/co2.py Client/dht22.py Client/light.py Client/light_mcp3008.py Sever/server.py Sever/alert.py Sever/detective.py Sever/app-new.py
```

ハードウェアが利用できない環境では、GPIO、SPI、シリアル通信の挙動を明確な理由なく
変更しないでください。将来的にモックやサンプルデータで検証しやすくするため、
ハードウェアアクセスは小さな関数に分けて扱うことを優先してください。

## 開発方針

- 変更は小さく保ち、既存のシンプルなスクリプト構成に合わせてください。
- 日本語を含むファイルでは UTF-8 を使用してください。
- タスクで別指定がない限り、Raspberry Pi のハードウェア前提を維持してください。
  - DHT22 は GPIO 26 を使用します。
  - CO2 センサーは `/dev/serial0` を使用します。
  - 光量センサーは SPI bus 0、device 0、channel 0 の MCP3008 経由で読み取ります。
- JSON スキーマを変更する場合は、送信側と受信側の両方を更新し、TCP 受信サーバー、
  Flask アラートエンドポイント、CSV ビューアのどれに影響するかを確認してください。
- CSV の列や保存場所を変更する場合は、CSV 書き出し処理と CSV ビューアを一緒に更新してください。
- `Sever/data/*.csv` はサンプルデータとして扱ってください。明示的な依頼がない限り、
  上書きや削除はしないでください。
- 重いフレームワークの追加は避けてください。このプロジェクトは現在、素の Python
  スクリプトと HTTP 表示用の Flask を中心に構成されています。
