#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Usage:
# 1. Start the TCP server in another terminal:
#    cd Server
#    python server.py -h 0.0.0.0 -p 8765
#
# 2. Send fake sensor data to the server:
#    cd Client
#    python fake_sensor_client.py
#
# 3. Send a specific test scenario:
#    python fake_sensor_client.py --scenario rising_co2
#
# 4. Create a CSV file directly without using the server:
#    python fake_sensor_client.py --csv-out fake-sensor.csv --scenario hot_room -c 30
#
# Scenarios:
# normal, rising_co2, dark_room, hot_room, unstable

import argparse
import csv
import datetime as dt
import json
import random
import socket
import sys
import time


SERVER = "127.0.0.1"
WAITING_PORT = 8765
COLUMNS = ["id", "timestamp", "temp", "humid", "co2", "light_percent"]
SCENARIOS = [
    ("normal", "普通の部屋"),
    ("rising_co2", "CO2が上がる"),
    ("dark_room", "暗い部屋"),
    ("hot_room", "暑くなる部屋"),
    ("unstable", "不安定なセンサ"),
]
OUTPUT_MODES = [
    ("send", "サーバへ送信"),
    ("print", "画面に表示"),
    ("csv", "CSV保存"),
]
COUNT_PRESETS = [
    (100, "100件    動作確認"),
    (300, "300件    AI予測用"),
    (1000, "1000件   長めの学習・検証"),
    ("custom", "自由入力  好きな件数を入力"),
]
INTERVAL_PRESETS = [
    (0.0, "0秒      できるだけ速く作る"),
    (0.1, "0.1秒    速めに送る"),
    (1.0, "1秒      通常"),
]


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def make_sensor_data(index, count, scenario):
    progress = index / max(count - 1, 1)

    temp = 24.0 + random.uniform(-0.4, 0.4)
    humid = 55.0 + random.uniform(-2.0, 2.0)
    co2 = 650 + random.uniform(-35, 35)
    light_percent = 65.0 + random.uniform(-5.0, 5.0)

    if scenario == "rising_co2":
        co2 = 600 + progress * 1200 + random.uniform(-45, 45)
        humid = 52.0 + progress * 8.0 + random.uniform(-2.0, 2.0)
    elif scenario == "dark_room":
        light_percent = 10.0 + random.uniform(-4.0, 4.0)
        temp = 23.0 + random.uniform(-0.5, 0.5)
    elif scenario == "hot_room":
        temp = 25.0 + progress * 7.0 + random.uniform(-0.5, 0.5)
        humid = 60.0 - progress * 12.0 + random.uniform(-2.0, 2.0)
    elif scenario == "unstable":
        temp += random.uniform(-3.0, 3.0)
        humid += random.uniform(-15.0, 15.0)
        co2 += random.uniform(-250, 650)
        light_percent += random.uniform(-45.0, 35.0)

    return {
        "temp": round(clamp(temp, -10.0, 50.0), 1),
        "humid": round(clamp(humid, 0.0, 100.0), 1),
        "co2": int(clamp(co2, 300, 5000)),
        "light_percent": round(clamp(light_percent, 0.0, 100.0), 1),
    }


def make_rows(count, interval, scenario):
    started_at = dt.datetime.now()
    rows = []
    for index in range(count):
        data = make_sensor_data(index, count, scenario)
        timestamp = started_at + dt.timedelta(seconds=index * interval)
        rows.append(
            [
                index,
                timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                data["temp"],
                data["humid"],
                data["co2"],
                data["light_percent"],
            ]
        )
    return rows


def write_csv(path, count, interval, scenario):
    rows = make_rows(count, interval, scenario)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    print(f"Saved test csv: {path}")


def send_json(host, port, count, interval, scenario):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client.connect((host, port))

        for index in range(count):
            data = make_sensor_data(index, count, scenario)
            message = json.dumps(data) + "\n"
            client.sendall(message.encode("utf-8"))
            print(message, end="")
            time.sleep(interval)


def print_json(count, scenario):
    for index in range(count):
        print(json.dumps(make_sensor_data(index, count, scenario)))


def scenario_label(scenario):
    labels = dict(SCENARIOS)
    return labels.get(scenario, scenario)


def output_label(output_mode):
    labels = dict(OUTPUT_MODES)
    return labels.get(output_mode, output_mode)


def prompt_choice(title, choices, default_number=1):
    while True:
        print()
        print(title)
        for number, (_, label) in enumerate(choices, start=1):
            default_mark = " (Enter)" if number == default_number else ""
            print(f"  {number}. {label}{default_mark}")

        answer = input(f"番号 [{default_number}]: ").strip()
        if answer == "":
            answer = str(default_number)

        if answer.isdigit():
            number = int(answer)
            if 1 <= number <= len(choices):
                return choices[number - 1][0]

        print("番号が正しくありません。もう一度入力してください。")


def prompt_int(label, default, min_value=1):
    while True:
        answer = input(f"{label} [{default}]: ").strip()
        if answer == "":
            return default

        try:
            value = int(answer)
        except ValueError:
            print("整数で入力してください。")
            continue

        if value >= min_value:
            return value

        print(f"{min_value}以上の整数で入力してください。")


def prompt_custom_int(label, example, min_value=1):
    while True:
        answer = input(f"{label}を入力してください（例: {example}）: ").strip()
        if answer == "":
            print("値を入力してください。")
            continue

        try:
            value = int(answer)
        except ValueError:
            print("整数で入力してください。")
            continue

        if value >= min_value:
            return value

        print(f"{min_value}以上の整数で入力してください。")


def prompt_count():
    choice = prompt_choice("件数を選んでください。", COUNT_PRESETS, default_number=2)
    if choice == "custom":
        return prompt_custom_int("件数", 5000)
    return choice


def prompt_float(label, default, min_value=0.0):
    while True:
        answer = input(f"{label} [{default}]: ").strip()
        if answer == "":
            return default

        try:
            value = float(answer)
        except ValueError:
            print("数値で入力してください。")
            continue

        if value >= min_value:
            return value

        print(f"{min_value}以上の数値で入力してください。")


def prompt_custom_float(label, example, min_value=0.0):
    while True:
        answer = input(f"{label}を入力してください（例: {example}）: ").strip()
        if answer == "":
            print("値を入力してください。")
            continue

        try:
            value = float(answer)
        except ValueError:
            print("数値で入力してください。")
            continue

        if value >= min_value:
            return value

        print(f"{min_value}以上の数値で入力してください。")


def prompt_interval():
    choice = prompt_choice("間隔秒を選んでください。", INTERVAL_PRESETS, default_number=1)
    return choice


def prompt_text(label, default):
    answer = input(f"{label} [{default}]: ").strip()
    return default if answer == "" else answer


def default_csv_path(scenario):
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    return f"fake-sensor-{scenario}-{timestamp}.csv"


def interactive_args():
    print("Fake sensor test menu")
    print("条件を番号で選ぶだけで、テスト用のセンサ値を作れます。")

    scenario = prompt_choice("条件を選んでください。", SCENARIOS)
    output_mode = prompt_choice("出力方法を選んでください。", OUTPUT_MODES)
    count = prompt_count()
    interval = prompt_interval()

    host = SERVER
    port = WAITING_PORT
    csv_out = None

    if output_mode == "send":
        host = prompt_text("送信先IP", SERVER)
        port = prompt_int("ポート", WAITING_PORT)
    elif output_mode == "csv":
        csv_out = prompt_text("CSVファイル名", default_csv_path(scenario))

    print()
    print("実行内容")
    print(f"  条件: {scenario_label(scenario)} ({scenario})")
    print(f"  件数: {count}")
    print(f"  間隔秒: {interval}")
    print(f"  出力方法: {output_label(output_mode)}")
    if output_mode == "send":
        print(f"  送信先: {host}:{port}")
    elif output_mode == "csv":
        print(f"  CSV: {csv_out}")
    input("Enterで開始します。")
    print()

    return argparse.Namespace(
        host=host,
        port=port,
        count=count,
        interval=interval,
        scenario=scenario,
        seed=None,
        dry_run=(output_mode == "print"),
        csv_out=csv_out,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate fake sensor data for week08 server and AI prediction tests."
    )
    parser.add_argument("-H", "--host", default=SERVER)
    parser.add_argument("-p", "--port", type=int, default=WAITING_PORT)
    parser.add_argument("-c", "--count", type=int, default=30)
    parser.add_argument("-i", "--interval", type=float, default=1.0)
    parser.add_argument(
        "-s",
        "--scenario",
        choices=["normal", "rising_co2", "dark_room", "hot_room", "unstable"],
        default="normal",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--csv-out", default=None)
    return parser.parse_args()


def main():
    if len(sys.argv) == 1:
        args = interactive_args()
    else:
        args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.csv_out:
        write_csv(args.csv_out, args.count, args.interval, args.scenario)
    elif args.dry_run:
        print_json(args.count, args.scenario)
    else:
        send_json(args.host, args.port, args.count, args.interval, args.scenario)


if __name__ == "__main__":
    main()
