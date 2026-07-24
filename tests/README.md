# テスト方針

このディレクトリには、リポジトリ全体のテストに関係するファイルを配置します。
Python の単体テストは `unittest`、ブラウザ操作を伴う E2E テストは Playwright を
使って実装します。

`alert.py`、`server.py`、`app.py`、`Client/` の Unit Test と、CSV ビューアの
E2E テストを配置しています。

## ディレクトリ構成

```text
tests/
  README.md              テスト方針と実行方法。
  requirements.txt       Unit Test と E2E テスト用の依存関係。
  unit/                  Python の unittest による単体テスト。
  e2e/                   Playwright によるブラウザ E2E テスト。
  fixtures/              テスト用の固定データ（現在は CSV）。
```

## 単体テスト

Python の単体テストは `tests/unit/` に配置します。ファイル名は
`test_*.py` とし、標準ライブラリの `unittest` モジュールで実装します。

実行例:

```bash
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests/unit -p "test_*.py"
```

現在は `alert.py` の通知と状態遷移、`server.py` の行追加・CSV保存・TCP受信、
`app.py` のCSV選択・平均値計算・データ追加・異常系、`Client/` のセンサー読み取り・
送信形式・CO2/光量ラッパーを検証しています。

`alert.py` のテストでは Slack Webhook 通信をモックするため、`Server/.env` や実際の
`SLACK_WEBHOOK_URL` は不要です。Unit Testへ実際のWebhook URLを記載しないでください。
Unit Test のシナリオは `docs/test-unit-scenario.md` を参照してください。

テスト対象の例:

- JSON データの整形やバリデーション処理
- CSV に保存する行データの組み立て処理
- Webhook へ送る通知文の生成処理
- ハードウェアアクセスを伴わない小さな関数

Raspberry Pi の GPIO、SPI、シリアル通信に直接依存する処理は、実機がない環境で
失敗しやすいため、単体テストではモックできる小さな関数に分けて検証します。

## E2E テスト

ブラウザを使う E2E テストは `tests/e2e/` に配置します。Flask の CSV ビューアなど、
画面表示とユーザー操作を確認したい機能は Playwright で検証します。

実行例:

```bash
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python -m pytest tests/e2e
```

E2E テストは Flask アプリを空いているローカルポートで自動起動し、Playwright の
Chromium からページへアクセスします。テストデータは本番用やサンプル用の CSV を
直接上書きせず、`tests/fixtures/csv_viewer/` のデータを一時ディレクトリへコピーして
使います。E2E テストのシナリオは `docs/test-e2e-scenario.md` を参照してください。

### ブラウザ画面を見ながら実行する

`E2E_HEADLESS=false` を指定するとChromiumの画面を表示できます。
`E2E_SLOW_MO` には各Playwright操作の待ち時間をミリ秒で指定します。

```bash
E2E_HEADLESS=false E2E_SLOW_MO=500 python -m pytest tests/e2e -s
```

1件だけ確認する場合は、テスト名を指定します。次の例では数値ソートだけを実行します。

```bash
E2E_HEADLESS=false E2E_SLOW_MO=1000 python -m pytest tests/e2e/test_csv_viewer.py::test_numeric_column_can_be_sorted -s
```

テストが終わるとブラウザも自動で閉じます。通常の自動実行では環境変数を付けず、
ヘッドレスモードを使ってください。

## テストデータの扱い

テストで使う固定データは `tests/fixtures/` に配置します。

- JSON 受信データの例は `.json` として保存します。
- CSV ビューア用のデータは `.csv` として保存します。
- 既存の `Server/data/*.csv` はサンプルデータとして扱い、テストから上書きしません。

一時ファイルが必要な場合は、テスト内で一時ディレクトリを作成し、テスト終了時に
削除します。

## 追加時のルール

- テスト名から、何を確認しているか分かるようにします。
- 外部サービスへ実際に通知を送るテストは避け、Webhook はモックします。
- CSV の列や JSON スキーマを変更した場合は、送信側、受信側、表示側の影響範囲を
  確認するテストを追加します。
- ハードウェアが必要な処理は、実機前提の手動確認と、自動化できる単体テストを
  分けて考えます。
