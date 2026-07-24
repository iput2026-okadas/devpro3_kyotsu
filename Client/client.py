#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import socket
import time

import co2
import dht22
import light


SERVER = "192.168.0.213"
WAITING_PORT = 8765
WAIT_INTERVAL = 5
SEND_COUNT = 6


def read_sensors():
    data = {
        "temp": None,
        "humid": None,
        "co2": None,
        "light_percent": None,
    }

    try:
        if hasattr(dht22, "get_dht_data_with_status"):
            temp, humid, _, _ = dht22.get_dht_data_with_status()
        else:
            temp, humid = dht22.get_dht_data()
        data["temp"] = temp
        data["humid"] = humid
    except Exception as e:
        print(f"DHT22 read failed: {e}")

    try:
        data["co2"] = co2.get_co2_data()
    except Exception as e:
        print(f"CO2 read failed: {e}")

    try:
        data["light_percent"] = light.get_light_percent()
    except Exception as e:
        print(f"Light sensor read failed: {e}")

    return data


def client_test(client_id, hostname_v1=SERVER, waiting_port_v1=WAITING_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_r_s:
        socket_r_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_r_s.connect((hostname_v1, waiting_port_v1))

        sent_count = 0
        while sent_count < SEND_COUNT:
            data = read_sensors()
            data["client_id"] = client_id
            print(
                "client_id: {client_id}, temp: {temp}, humid: {humid}, "
                "co2: {co2}, light: {light_percent} %".format(
                    **data
                )
            )

            missing = [name for name, value in data.items() if value is None]
            if missing:
                print(
                    "Sensor data incomplete; waiting for next measurement: "
                    + ", ".join(missing)
                )
            else:
                data_s = (json.dumps(data) + "\n").encode("utf-8")
                socket_r_s.sendall(data_s)
                sent_count += 1

            time.sleep(WAIT_INTERVAL)


def non_empty_client_id(value):
    client_id = value.strip()
    if not client_id:
        raise argparse.ArgumentTypeError("client ID must not be empty")
    return client_id


def parse_arguments(args=None):
    parser = argparse.ArgumentParser(
        description="センサーデータをTCPサーバーへ送信します。",
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="このヘルプを表示します。")
    parser.add_argument("-h", "--host", default=SERVER, help="接続先サーバーのホスト名")
    parser.add_argument("-p", "--port", type=int, default=WAITING_PORT, help="接続先ポート")
    parser.add_argument(
        "-i",
        "--client-id",
        required=True,
        type=non_empty_client_id,
        help="このRaspberry Piを識別するID名",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    arguments = parse_arguments()

    try:
        client_test(arguments.client_id, arguments.host, arguments.port)
    except KeyboardInterrupt:
        print("End of this client.")
    finally:
        if hasattr(dht22, "close"):
            dht22.close()
        if hasattr(co2, "close"):
            co2.close()
