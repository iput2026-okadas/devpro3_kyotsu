#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    import spidev
except ImportError:
    spidev = None


class MCP3008Error(Exception):
    pass


class MCP3008:
    """MCP3008 ADC reader for Raspberry Pi."""

    def __init__(self, spi_bus=0, spi_device=0, channel=0, max_speed_hz=1350000):
        if not 0 <= channel <= 7:
            raise ValueError("channel must be between 0 and 7")

        if spidev is None:
            raise MCP3008Error("spidev is required to use MCP3008 on this platform")

        self.channel = int(channel)
        self._spi = spidev.SpiDev()
        self._spi.open(spi_bus, spi_device)
        self._spi.max_speed_hz = max_speed_hz
        self._spi.mode = 0

    def read_channel(self, channel=None):
        """Read the raw 10-bit ADC value from the selected MCP3008 channel."""
        if channel is None:
            channel = self.channel

        if not 0 <= channel <= 7:
            raise ValueError("channel must be between 0 and 7")

        request = [1, (8 + channel) << 4, 0]
        response = self._spi.xfer2(request)
        if len(response) != 3:
            raise MCP3008Error("Unexpected response length from MCP3008")

        raw_value = ((response[1] & 3) << 8) | response[2]
        return int(raw_value)

    def read_percent(self, channel=None):
        """Read raw ADC data and convert it to a 0-100% value."""
        raw_value = self.read_channel(channel)
        return round((raw_value / 1023.0) * 100.0, 1)

    def close(self):
        try:
            if self._spi is not None:
                self._spi.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
