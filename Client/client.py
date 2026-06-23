#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import socket
import sys
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


def client_test(hostname_v1=SERVER, waiting_port_v1=WAITING_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_r_s:
        socket_r_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_r_s.connect((hostname_v1, waiting_port_v1))

        for _ in range(SEND_COUNT):
            data = read_sensors()
            print(
                "temp: {temp}, humid: {humid}, co2: {co2}, light: {light_percent} %".format(
                    **data
                )
            )
            data_s = (json.dumps(data) + "\n").encode("utf-8")
            socket_r_s.sendall(data_s)
            time.sleep(WAIT_INTERVAL)


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

    try:
        client_test(hostname_v, waiting_port_v)
    except KeyboardInterrupt:
        print("End of this client.")
    finally:
        if hasattr(co2, "close"):
            co2.close()
