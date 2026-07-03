import json
import sys
import time
import socket
import threading
import datetime as dt
import csv
from pathlib import Path

import alert

SERVER = '127.0.0.1'
WAITING_PORT = 8765
BACKLOG = 5
LOOP_INTERVAL = 5
DATA_DIR = Path(__file__).resolve().parent / "data"

# CSV関係
column = ["id", "timestamp", "temp", "humid"]
data = []

def add_data(data_dict):
    print(f"add_data temp: {data_dict["temp"]}, humid: {data_dict["humid"]}")
    data.append([
        len(data),
        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data_dict["temp"],
        data_dict["humid"]
    ])

def save_data():
    now = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    output_path = DATA_DIR / f"data-{now}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(column)
        writer.writerows(data)

    print(f"\n\nSave csv: {output_path}")

def recv_data1024(socket1, client_addr):
    print(f"接続: {client_addr}")
    try:
        while True:
            data_r = socket1.recv(1024)
            if not data_r:              # 正常切断（FIN）
                break
            data_dict = json.loads(data_r.decode('utf-8'))
            add_data(data_dict)
            alert.process_sensor_data(data_dict)
    except ConnectionResetError:
        print(f"強制切断: {client_addr}")
    except Exception as e:
        print(f"エラー: {e}")
    finally:
        socket1.close()
        print(f"切断: {client_addr}")

def server_test(node_s=SERVER, port_s=WAITING_PORT):
    stop_event = threading.Event()
    socket_w = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_w.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_w.bind((node_s, port_s)) 
    socket_w.listen(BACKLOG)

    def accept_connections():
        while not stop_event.is_set():
            try:
                socket_w.settimeout(1)
                socket_s_r, client_address = socket_w.accept()
                thread = threading.Thread(target=recv_data1024,
                                          args=(socket_s_r, client_address),
                                          daemon=True)
                thread.start()
            except socket.timeout:
                continue

    accept_thread = threading.Thread(target=accept_connections)
    accept_thread.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        accept_thread.join()
        socket_w.close()
        save_data()

if __name__ == '__main__':
    sys_argc = len(sys.argv)
    count = 1
    hostname_v = SERVER
    waiting_port_v = WAITING_PORT

    while True:
        if(count >= sys_argc): break

        option_key = sys.argv[count]
        if ("-h" == option_key):
            count = count + 1
            hostname_v = sys.argv[count]

        if ("-p" == option_key):
            count = count + 1
            waiting_port_v = int(sys.argv[count])

        count = count + 1

    server_test(hostname_v, waiting_port_v)
