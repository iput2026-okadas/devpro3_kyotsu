# Raspberry Pi sensor client

Raspberry PiでDHT22とCO2センサを読み取り、PC側のTCPサーバーへJSONで送信するクライアントです。

## Files

- `client.py`: DHT22とCO2を読み取り、サーバーへ送信します。
- `dht22.py`: DHT22読み取り用の薄いラッパーです。
- `dht22_takemoto.py`: DHT22のGPIO読み取り実装です。
- `co2.py`: MH-Z19系CO2センサをUART(`/dev/serial0`)で読み取ります。
- `optional/`: 現在の`client.py`では使っていない参考実装です。

## Run

PC側サーバーのIPアドレスを指定して実行します。

```bash
cd ~/devpro3/week08/raspi
sudo ~/devpro3/venv313/bin/python client.py -h PCのIPアドレス -p 8765
```

例:

```bash
sudo ~/devpro3/venv313/bin/python client.py -h 10.192.138.237 -p 8765
```

送信するJSONは次の形式です。

```json
{"temp": 24.8, "humid": 60.2, "co2": 1235}
```

## Notes

- PC側サーバーは`0.0.0.0:8765`で待ち受けてください。
- `localhost`は実行している機械自身を指します。Raspberry PiからPCへ送る場合はPCのIPアドレスを指定します。
- CO2センサは`/dev/serial0`を使うため、実行には`sudo`が必要な場合があります。
- `serial-getty@ttyS0.service`が有効だとCO2センサのUARTと競合することがあります。
- DHT22は読み取りに失敗することがあります。その場合、`client.py`は`temp`と`humid`を`None`にして送信します。
