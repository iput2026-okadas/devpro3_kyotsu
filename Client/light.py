#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from light_mcp3008 import MCP3008, MCP3008Error


LIGHT_CHANNEL = 0
SPI_BUS = 0
SPI_DEVICE = 0


def get_light_percent(channel=LIGHT_CHANNEL, spi_bus=SPI_BUS, spi_device=SPI_DEVICE):
    """Read the photoresistor voltage from MCP3008 and return a percent value."""
    try:
        with MCP3008(spi_bus=spi_bus, spi_device=spi_device, channel=channel) as adc:
            return adc.read_percent(channel)
    except MCP3008Error:
        raise
    except Exception as e:
        raise MCP3008Error(f"Failed to read light sensor: {e}") from e


if __name__ == "__main__":
    try:
        value = get_light_percent()
        print(f"Light intensity: {value} %")
    except Exception as e:
        print(f"Error reading light sensor: {e}")
