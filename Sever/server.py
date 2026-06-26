#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import datetime as dt
import json
import socket
import sys
import threading
import time
from pathlib import Path


SERVER = '0.0.0.0'
WAITING_PORT = 8765
BACKLOG = 5

BASE_DIR = Path(__file__).resolve().parent
COLUMNS = ["id", "timestamp", "temp", "humid", "co2", "light_percent"]
data = []
data_lock = threading.Lock()


def add_data(data_dict):
    row = [
        len(data),
        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data_dict.get("temp"),
        data_dict.get("humid"),
        data_dict.get("co2"),
        data_dict.get("light_percent"),
    ]
    with data_lock:
        data.append(row)

    print(
        "received temp: {temp}, humid: {humid}, co2: {co2}, light: {light_percent}".format(
            temp=data_dict.get("temp"),
            humid=data_dict.get("humid"),
            co2=data_dict.get("co2"),
            light_percent=data_dict.get("light_percent"),
        )
    )


def save_data():
    if not data:
        print("No data to save.")
        return

    now = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    csv_path = BASE_DIR / f"data-{now}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(data)

    print(f"\nSaved csv: {csv_path.name}")


def recv_data1024(socket1, client_addr):
    print(f"connected: {client_addr}")
    buffer = ""
    try:
        while True:
            data_r = socket1.recv(1024)
            if not data_r:
                break

            buffer += data_r.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                add_data(json.loads(line))

        if buffer.strip():
            add_data(json.loads(buffer.strip()))

    except ConnectionResetError:
        print(f"connection reset: {client_addr}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error from {client_addr}: {e}")
    except Exception as e:
        print(f"server error from {client_addr}: {e}")
    finally:
        socket1.close()
        print(f"closed: {client_addr}")


def server_test(node_s=SERVER, port_s=WAITING_PORT):
    stop_event = threading.Event()
    socket_w = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_w.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_w.bind((node_s, port_s))
    socket_w.listen(BACKLOG)
    print(f"Waiting for sensor data on {node_s}:{port_s}")

    def accept_connections():
        while not stop_event.is_set():
            try:
                socket_w.settimeout(1)
                socket_s_r, client_address = socket_w.accept()
                thread = threading.Thread(
                    target=recv_data1024,
                    args=(socket_s_r, client_address),
                    daemon=True,
                )
                thread.start()
            except socket.timeout:
                continue
            except OSError:
                break

    accept_thread = threading.Thread(target=accept_connections, daemon=True)
    accept_thread.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        stop_event.set()
        socket_w.close()
        accept_thread.join(timeout=2)
        save_data()


if __name__ == "__main__":
    sys_argc = len(sys.argv)
    count = 1
    hostname_v = SERVER
    waiting_port_v = WAITING_PORT

    while count < sys_argc:
        option_key = sys.argv[count]
        if option_key == "-h":
            count += 1
            hostname_v = sys.argv[count]
        elif option_key == "-p":
            count += 1
            waiting_port_v = int(sys.argv[count])
        count += 1

    server_test(hostname_v, waiting_port_v)
