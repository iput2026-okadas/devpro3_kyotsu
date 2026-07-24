import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock


CLIENT_DIR = Path(__file__).resolve().parents[2] / "Client"


class FakeSpiDev:
    instances = []

    def __init__(self):
        self.open = MagicMock()
        self.close = MagicMock()
        self.xfer2 = MagicMock(return_value=[0, 0, 0])
        self.max_speed_hz = None
        self.mode = None
        FakeSpiDev.instances.append(self)


class FakeMCP3008Error(Exception):
    pass


class TestMCP3008(unittest.TestCase):
    def setUp(self):
        self.original_path = list(sys.path)
        self.original_module = sys.modules.get("light_mcp3008")
        self.original_spidev = sys.modules.get("spidev")
        FakeSpiDev.instances = []

        sys.modules["spidev"] = types.SimpleNamespace(SpiDev=FakeSpiDev)
        sys.modules.pop("light_mcp3008", None)
        sys.path.insert(0, str(CLIENT_DIR))
        self.light_mcp3008 = importlib.import_module("light_mcp3008")
        self.addCleanup(self._restore_imports)

    def _restore_imports(self):
        sys.path[:] = self.original_path
        if self.original_module is None:
            sys.modules.pop("light_mcp3008", None)
        else:
            sys.modules["light_mcp3008"] = self.original_module

        if self.original_spidev is None:
            sys.modules.pop("spidev", None)
        else:
            sys.modules["spidev"] = self.original_spidev

    def test_init_opens_spi_and_sets_config(self):
        adc = self.light_mcp3008.MCP3008(spi_bus=1, spi_device=2, channel=3)

        spi = FakeSpiDev.instances[-1]
        spi.open.assert_called_once_with(1, 2)
        self.assertEqual(spi.max_speed_hz, 1350000)
        self.assertEqual(spi.mode, 0)
        self.assertEqual(adc.channel, 3)

    def test_init_rejects_invalid_channel(self):
        for channel in (-1, 8):
            with self.subTest(channel=channel):
                with self.assertRaisesRegex(ValueError, "channel must be between 0 and 7"):
                    self.light_mcp3008.MCP3008(channel=channel)

    def test_init_requires_spidev(self):
        self.light_mcp3008.spidev = None

        with self.assertRaisesRegex(
            self.light_mcp3008.MCP3008Error,
            "spidev is required",
        ):
            self.light_mcp3008.MCP3008(channel=0)

    def test_read_channel_sends_mcp3008_request_and_returns_raw_value(self):
        adc = self.light_mcp3008.MCP3008(channel=0)
        spi = FakeSpiDev.instances[-1]
        spi.xfer2.return_value = [0, 0b00000010, 0b10101010]

        result = adc.read_channel(2)

        self.assertEqual(result, 682)
        spi.xfer2.assert_called_once_with([1, (8 + 2) << 4, 0])

    def test_read_channel_rejects_invalid_channel(self):
        adc = self.light_mcp3008.MCP3008(channel=0)

        with self.assertRaisesRegex(ValueError, "channel must be between 0 and 7"):
            adc.read_channel(9)

    def test_read_channel_rejects_unexpected_response_length(self):
        adc = self.light_mcp3008.MCP3008(channel=0)
        FakeSpiDev.instances[-1].xfer2.return_value = [0, 1]

        with self.assertRaisesRegex(
            self.light_mcp3008.MCP3008Error,
            "Unexpected response length",
        ):
            adc.read_channel()

    def test_read_percent_converts_raw_value_to_percent(self):
        adc = self.light_mcp3008.MCP3008(channel=0)
        adc.read_channel = MagicMock(return_value=512)

        self.assertEqual(adc.read_percent(), 50.0)

    def test_close_ignores_spi_close_error(self):
        adc = self.light_mcp3008.MCP3008(channel=0)
        FakeSpiDev.instances[-1].close.side_effect = RuntimeError("close failed")

        adc.close()

    def test_context_manager_closes_spi(self):
        with self.light_mcp3008.MCP3008(channel=0):
            pass

        FakeSpiDev.instances[-1].close.assert_called_once_with()


class TestLightWrapper(unittest.TestCase):
    def setUp(self):
        self.original_path = list(sys.path)
        self.original_light = sys.modules.get("light")
        self.original_light_mcp3008 = sys.modules.get("light_mcp3008")

        self.fake_adc = MagicMock()
        self.fake_adc.__enter__.return_value = self.fake_adc
        self.fake_adc.__exit__.return_value = None
        self.fake_adc.read_percent.return_value = 42.5
        self.fake_mcp3008 = MagicMock(return_value=self.fake_adc)

        sys.modules["light_mcp3008"] = types.SimpleNamespace(
            MCP3008=self.fake_mcp3008,
            MCP3008Error=FakeMCP3008Error,
        )
        sys.modules.pop("light", None)
        sys.path.insert(0, str(CLIENT_DIR))
        self.light = importlib.import_module("light")
        self.addCleanup(self._restore_imports)

    def _restore_imports(self):
        sys.path[:] = self.original_path
        if self.original_light is None:
            sys.modules.pop("light", None)
        else:
            sys.modules["light"] = self.original_light

        if self.original_light_mcp3008 is None:
            sys.modules.pop("light_mcp3008", None)
        else:
            sys.modules["light_mcp3008"] = self.original_light_mcp3008

    def test_get_light_percent_reads_adc_percent(self):
        result = self.light.get_light_percent(channel=2, spi_bus=1, spi_device=3)

        self.assertEqual(result, 42.5)
        self.fake_mcp3008.assert_called_once_with(
            spi_bus=1,
            spi_device=3,
            channel=2,
        )
        self.fake_adc.read_percent.assert_called_once_with(2)

    def test_get_light_percent_reraises_mcp3008_error(self):
        self.fake_mcp3008.side_effect = FakeMCP3008Error("no spi")

        with self.assertRaisesRegex(FakeMCP3008Error, "no spi"):
            self.light.get_light_percent()

    def test_get_light_percent_wraps_unexpected_error(self):
        self.fake_mcp3008.side_effect = RuntimeError("boom")

        with self.assertRaisesRegex(FakeMCP3008Error, "Failed to read light sensor"):
            self.light.get_light_percent()


if __name__ == "__main__":
    unittest.main()
