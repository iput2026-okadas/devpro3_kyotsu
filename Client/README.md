# Raspberry Pi センサークライアント

`Client/` には、Raspberry Pi 上でセンサー値を読み取り、PC 側の TCP サーバーへ
JSON 形式で送信するためのプログラムを配置しています。

## ファイル構成

```text
Client/
  client.py            センサー値を読み取り、TCP サーバーへ JSON を送信する。
  dht22.py             DHT22 読み取り用の薄いラッパー。
  dht22_takemoto.py    lgpio を使う DHT22 実装。
  co2.py               MH-Z19 系 CO2 センサーを UART で読み取る。
  light.py             光量センサー読み取り用の薄いラッパー。
  light_mcp3008.py     MCP3008 SPI ADC 経由で光量を読み取る。
  requirements.txt     Raspberry Pi ハードウェア用の依存関係。
```

## セットアップ

Raspberry Pi 側で依存関係をインストールします。

```bash
cd Client
python -m pip install -r requirements.txt
```

CO2 センサーは `/dev/serial0`、光量センサーは SPI 接続の MCP3008 を使います。
環境によっては、実行時に `sudo` が必要です。

## 実行方法

先に PC 側で `Sever/server.py` を起動し、`0.0.0.0:8765` などで待ち受けてください。
その後、Raspberry Pi 側で PC の IP アドレスを指定してクライアントを起動します。

```bash
sudo python client.py -h <server-ip-address> -p 8765
```

例:

```bash
sudo python client.py -h 192.168.0.213 -p 8765
```

送信する JSON は次の形式です。

```json
{"temp": 24.8, "humid": 60.2, "co2": 1235, "light_percent": 48.5}
```

## 注意点

- `localhost` は実行している機械自身を指します。Raspberry Pi から PC へ送る場合は
  PC の IP アドレスを指定してください。
- DHT22 は GPIO 26 を使います。
- CO2 センサーは `/dev/serial0` を使います。
- 光量センサーは SPI bus 0、device 0、channel 0 の MCP3008 経由で読み取ります。
- DHT22 の読み取りに失敗した場合、`client.py` は `temp` と `humid` を `None` にして
  送信します。
- CO2 や光量の読み取りに失敗した場合も、該当値は `None` のまま送信されます。
