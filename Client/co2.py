#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import sys

try:
    import serial
except ImportError as e:
    raise ImportError("pyserial module is required. Install it with: pip install pyserial") from e


SERIAL_DEVICE = "/dev/serial0"
BAUD_RATE = 9600
WARM_UP_TIME = 10
READ_COMMAND = b"\xff\x01\x86\x00\x00\x00\x00\x00\x79"

_initialized_time = time.time()


class CO2ReadError(Exception):
    pass


def _checksum(data):
    return (0xFF - (sum(data[1:8]) & 0xFF) + 1) & 0xFF


def _read_co2_once():
    with serial.Serial(
        SERIAL_DEVICE,
        baudrate=BAUD_RATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1.0,
    ) as ser:
        time.sleep(1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(READ_COMMAND)
        ser.flush()
        response = ser.read(9)

    if len(response) == 8 and response[0] == 0x86:
        response = b"\xff" + response

    if len(response) != 9:
        raise CO2ReadError(
            f"Invalid response length: {len(response)} ({response.hex(' ')})"
        )

    if response[0] != 0xFF or response[1] != 0x86:
        raise CO2ReadError(f"Invalid CO2 sensor response header: {response.hex(' ')}")

    if response[8] != _checksum(response):
        raise CO2ReadError(f"Invalid CO2 sensor checksum: {response.hex(' ')}")

    return response[2] * 256 + response[3]


def get_co2_data():
    """Read CO2 concentration from the MH-Z19 sensor and return ppm as int."""
    elapsed = time.time() - _initialized_time
    if elapsed < WARM_UP_TIME:
        time.sleep(WARM_UP_TIME - elapsed)

    try:
        return int(_read_co2_once())
    except CO2ReadError:
        raise
    except Exception as e:
        raise CO2ReadError(f"CO2 sensor read failed: {e}") from e


def print_co2_data():
    co2_ppm = get_co2_data()
    print(f"CO2: {co2_ppm} ppm")


def close():
    pass


if __name__ == "__main__":
    try:
        print_co2_data()
    except CO2ReadError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("End of CO2 reader.")
