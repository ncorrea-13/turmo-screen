"""Runnable checks for turmo's parsing/packing/branching logic.

Run: python -m unittest discover tests
No hardware needed — serial I/O is mocked.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from turmo.codecs import encode_pixels
from turmo.config import parse_bg
from turmo.metrics import fetch_fleet_hosts
from turmo.renderers import render_fleet_dashboard
from turmo.serial_device import TurmoSerial


class ParseBgTests(unittest.TestCase):
    def test_named_colors(self):
        self.assertEqual(parse_bg("black"), (0, 0, 0))
        self.assertEqual(parse_bg("white"), (255, 255, 255))

    def test_hex(self):
        self.assertEqual(parse_bg("#e15cff"), (225, 92, 255))

    def test_invalid_raises(self):
        with self.assertRaises(Exception):
            parse_bg("not-a-color")


class EncodePixelsTests(unittest.TestCase):
    def test_rgb565le_known_pixel(self):
        img = Image.new("RGB", (1, 1), (255, 0, 0))  # pure red -> 0xF800
        raw = encode_pixels(img, pixel_format="rgb565le")
        self.assertEqual(raw, bytes([0x00, 0xF8]))

    def test_output_length_matches_dimensions(self):
        img = Image.new("RGB", (4, 3), (0, 255, 0))
        raw = encode_pixels(img, pixel_format="rgb565le")
        self.assertEqual(len(raw), 4 * 3 * 2)

    def test_unsupported_format_raises(self):
        img = Image.new("RGB", (1, 1))
        with self.assertRaises(ValueError):
            encode_pixels(img, pixel_format="nope")


class RevaPackingTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("serial.Serial", return_value=MagicMock())
        self.addCleanup(patcher.stop)
        patcher.start()
        self.dev = TurmoSerial("fake")

    def test_pack_reva_command_round_trips(self):
        packet = self.dev.pack_reva_command(197, 0, 0, 319, 479)
        self.assertEqual(len(packet), 6)
        self.assertEqual(packet[5], 197)
        x = (packet[0] << 2) | (packet[1] >> 6)
        y = ((packet[1] & 0x3F) << 4) | (packet[2] >> 4)
        ex = ((packet[2] & 0x0F) << 6) | (packet[3] >> 2)
        ey = ((packet[3] & 0x03) << 8) | packet[4]
        self.assertEqual((x, y, ex, ey), (0, 0, 319, 479))

    def test_clamps_negative_to_zero(self):
        packet = self.dev.pack_reva_command(101, -5, -1, -1, -1)
        self.assertEqual(packet, bytes([0, 0, 0, 0, 0, 101]))


class FetchFleetHostsTests(unittest.TestCase):
    def test_returns_empty_on_missing_binary(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(fetch_fleet_hosts(hub="x:9090"), [])

    def test_returns_empty_on_bad_json(self):
        fake = MagicMock(stdout="not json")
        with patch("subprocess.run", return_value=fake):
            self.assertEqual(fetch_fleet_hosts(hub="x:9090"), [])

    def test_parses_valid_json_list(self):
        fake = MagicMock(stdout=json.dumps([{"id": "a", "state": "online"}]))
        with patch("subprocess.run", return_value=fake):
            hosts = fetch_fleet_hosts(hub="x:9090")
        self.assertEqual(hosts, [{"id": "a", "state": "online"}])

    def test_token_passed_via_env_not_argv(self):
        fake = MagicMock(stdout="[]")
        with patch("subprocess.run", return_value=fake) as mock_run:
            fetch_fleet_hosts(hub="x:9090", token="s3cr3t")
        args, kwargs = mock_run.call_args
        self.assertNotIn("s3cr3t", args[0])
        self.assertEqual(kwargs["env"]["HEIMDALL_TOKEN"], "s3cr3t")

    def test_rejects_non_list_json(self):
        fake = MagicMock(stdout=json.dumps({"not": "a list"}))
        with patch("subprocess.run", return_value=fake):
            self.assertEqual(fetch_fleet_hosts(hub="x:9090"), [])


class RenderFleetDashboardTests(unittest.TestCase):
    def test_empty_fleet_does_not_crash(self):
        with patch("turmo.renderers.fetch_fleet_hosts", return_value=[]):
            img = render_fleet_dashboard(320, 480)
        self.assertEqual(img.size, (320, 480))

    def test_renders_with_hosts(self):
        hosts = [
            {"id": "b", "state": "offline", "metrics": {}},
            {"id": "a", "state": "online", "metrics": {"cpu.util": 12.3, "mem.used": 40.0, "disk.used": 55.0}},
        ]
        with patch("turmo.renderers.fetch_fleet_hosts", return_value=hosts):
            img = render_fleet_dashboard(320, 480)
        self.assertEqual(img.size, (320, 480))


if __name__ == "__main__":
    unittest.main()
