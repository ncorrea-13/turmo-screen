"""Shared defaults and protocol constants for TURMO Linux."""

DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 480
DEFAULT_BAUD = 4_000_000
DEFAULT_PIXEL_FORMAT = "rgb565le"

MAGIC_1 = 0xCF
MAGIC_2 = 0xEF
USB2_PACKET_LEN = 250

PIXEL_FORMATS = [
    "bgra", "rgba", "argb", "abgr", "rgbx", "bgrx", "xrgb", "xbgr",
    "rgb888", "bgr888", "rgb565le", "bgr565le", "rgb565be", "bgr565be",
]

RGB565_FORMATS = {"rgb565le", "bgr565le", "rgb565be", "bgr565be"}
