# サーバー側プログラム

`Sever/` には、Raspberry Pi から送られてくるセンサーデータを受信・保存・表示する
ためのプログラムを配置しています。

注意: ディレクトリ名は `Server/` ではなく `Sever/` です。リポジトリの既存構成に
合わせて、この名前を使用します。

## ファイル構成

```text
Sever/
  server.py            TCP JSON 受信サーバーと CSV 書き出し処理。
  app-new.py           Flask 製の CSV ビューア。
  alert.py             CO2 アラート用の Webhook 通知判定モジュール。
  detective.py         気温変化原因分類の決定木デモ。
  templates/           CSV ビューア用 HTML テンプレート。
  static/              CSV ビューア用 CSS と JavaScript。
  data/                既存の CSV サンプル。
  requirements.txt     サーバー側データ分析用の依存関係。
```

## セットアップ

```bash
cd Sever
python -m pip install -r requirements.txt
```

## TCP 受信サーバー

`server.py` は TCP ソケットで JSON データを受信し、メモリ上に保持します。
受信したデータは `alert.py` の `process_sensor_data()` にも渡され、CO2 濃度に応じた
Webhook 通知判定に使われます。
`Ctrl+C` で終了したタイミングで、受信済みデータを `data-YYYYMMDDHHMMSS.csv` として
`Sever/` 直下に保存します。

起動例:

```bash
python server.py -h 0.0.0.0 -p 8765
```

現在 CSV に保存する列は `id`, `timestamp`, `temp`, `humid` です。
クライアントからは `co2` と `light_percent` も送られますが、現状の `server.py` では
CSV 保存対象には含まれていません。

## CSV ビューア

`app-new.py` は `Sever/` 直下の `data-*.csv` を探し、ブラウザで一覧表示します。

起動例:

```bash
python app-new.py
```

ブラウザで `http://localhost:5001/` を開きます。

## Webhook アラート

`alert.py` は HTTP エンドポイントではなく、`server.py` から呼び出される通知判定
モジュールです。`server.py` が TCP で受信した JSON を `process_sensor_data()` へ渡し、
CO2 濃度に応じて Discord または Slack の Webhook へ通知します。

Webhook URL は `WEBHOOK_URL` 環境変数で指定します。実際の URL はコミットしないでください。

```bash
WEBHOOK_URL="<discord-or-slack-webhook-url>" python server.py -h 0.0.0.0 -p 8765
```

通知判定で扱う JSON は `Client/client.py` が送信する形式と同じです。

```json
{"temp": 24.8, "humid": 60.2, "co2": 1235, "light_percent": 48.5}
```

## 気温変化原因分類デモ

`detective.py` は `numpy`, `pandas`, `scikit-learn` を使い、気温変化の原因を
決定木で分類するデモです。

実行例:

```bash
python detective.py
```
