"""Pixel encoders for USB display framebuffers."""

from __future__ import annotations

from PIL import Image

from .image_ops import normalize_color_space

def encode_pixels(img: Image.Image, *, pixel_format: str, x_byte: int = 0) -> bytes:
    """Encode a PIL image into raw bytes for different USB display revisions.

    For TURMO 3.5-inch tested by user: --pixel-format rgbx.

    PNG/JPEG/palette/alpha images are always normalized to RGB before packing. This
    prevents alpha/palette PNGs from breaking the colors while test patterns look correct.
    """
    fmt = pixel_format.lower()
    x = max(0, min(255, int(x_byte)))

    rgb = normalize_color_space(img)

    if fmt in {"rgba", "bgra", "argb", "abgr", "rgbx", "bgrx", "xrgb", "xbgr"}:
        r, g, b = rgb.split()
        const = Image.new("L", rgb.size, x)
        alpha = Image.new("L", rgb.size, 255)
        channels = {
            "r": r,
            "g": g,
            "b": b,
            "a": alpha,
            "x": const,
        }
        order = {
            "rgba": "rgba",
            "bgra": "bgra",
            "argb": "argb",
            "abgr": "abgr",
            "rgbx": "rgbx",
            "bgrx": "bgrx",
            "xrgb": "xrgb",
            "xbgr": "xbgr",
        }[fmt]
        return Image.merge("RGBA", tuple(channels[c] for c in order)).tobytes()

    if fmt == "rgb888":
        return rgb.tobytes()
    if fmt == "bgr888":
        r, g, b = rgb.split()
        return Image.merge("RGB", (b, g, r)).tobytes()

    if fmt in {"rgb565le", "bgr565le", "rgb565be", "bgr565be"}:
        data = rgb.tobytes()
        out = bytearray((len(data) // 3) * 2)
        little = fmt.endswith("le")
        bgr = fmt.startswith("bgr")
        j = 0
        for i in range(0, len(data), 3):
            r, g, b = data[i], data[i + 1], data[i + 2]
            if bgr:
                r, b = b, r
            value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            if little:
                out[j] = value & 0xFF
                out[j + 1] = (value >> 8) & 0xFF
            else:
                out[j] = (value >> 8) & 0xFF
                out[j + 1] = value & 0xFF
            j += 2
        return bytes(out)

    raise ValueError(f"Unsupported pixel format: {pixel_format}")

def encode_solid_pixels(pixel_count: int, *, color: tuple[int, int, int], pixel_format: str, x_byte: int = 0) -> bytes:
    """Encode N solid-color pixels. Used for cursor/pointer padding experiments."""
    pixel_count = max(0, int(pixel_count))
    if pixel_count <= 0:
        return b""
    img = Image.new("RGB", (pixel_count, 1), color)
    return encode_pixels(img, pixel_format=pixel_format, x_byte=x_byte)
