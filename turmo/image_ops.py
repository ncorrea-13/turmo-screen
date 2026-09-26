"""Image normalization, fitting, rotation and framebuffer helpers."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageOps

from .constants import DEFAULT_HEIGHT, DEFAULT_WIDTH

def roll_framebuffer(img: Image.Image, roll_x: int = 0, roll_y: int = 0) -> Image.Image:
    """Circularly shift framebuffer content without changing its size.

    This is useful when the display's internal write pointer starts at a fixed
    offset. It does not fix cumulative cursor drift, but it can compensate a
    stable top-left offset.
    """
    roll_x = int(roll_x)
    roll_y = int(roll_y)
    if roll_x == 0 and roll_y == 0:
        return img
    return ImageChops.offset(normalize_color_space(img), roll_x, roll_y)

def normalize_color_space(img: Image.Image, bg: tuple[int, int, int] = (0, 0, 0)) -> Image.Image:
    """Return plain RGB image. Handles PNG palette and alpha safely."""
    img = ImageOps.exif_transpose(img)
    if img.mode == "RGB":
        return img
    rgba = img.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (*bg, 255))
    return Image.alpha_composite(background, rgba).convert("RGB")

def fit_to_screen(
    img: Image.Image,
    width: int,
    height: int,
    *,
    fit: str = "contain",
    bg: tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """Place image into a full-size RGB screen canvas.

    The device should always receive a full framebuffer. To make a picture smaller,
    we resize/pad inside a 320x480 canvas, not by changing --width/--height.
    """
    img = normalize_color_space(img, bg=bg)
    fit = fit.lower()

    if fit == "stretch":
        return img.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")

    if fit == "cover":
        # Crop to fill the entire screen.
        return ImageOps.fit(img, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).convert("RGB")

    if fit != "contain":
        raise ValueError("--fit must be contain, cover, or stretch")

    # Keep aspect ratio and add black bars.
    fitted = ImageOps.contain(img, (width, height), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), bg)
    x = (width - fitted.width) // 2
    y = (height - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return canvas

def transform_image_colors(
    img: Image.Image,
    *,
    bg: tuple[int, int, int] = (0, 0, 0),
    green_to_bg: bool = False,
    red_to_blue: bool = False,
    force_black: bool = False,
    black_threshold: int = 45,
) -> Image.Image:
    """Optional color cleanup for external images.

    This is useful for small USB screens where PNG palette/alpha images and
    anti-aliased backgrounds can look weird after conversion.

    - green_to_bg: replaces green-ish background pixels with --bg / --pink-bg.
    - red_to_blue: replaces red cheek-like pixels with bright blue.
    - force_black: snaps near-black outline pixels back to true black.
    """
    rgb = normalize_color_space(img, bg=bg)
    data = bytearray(rgb.tobytes())
    bt = max(0, min(255, int(black_threshold)))

    for i in range(0, len(data), 3):
        r, g, b = data[i], data[i + 1], data[i + 2]

        # Replace the original muted green background from the uploaded cat PNG.
        # Condition is intentionally broad but avoids white fur and black outlines.
        if green_to_bg and g >= 55 and g > r * 1.10 and g > b * 1.10 and r < 170 and b < 170:
            data[i], data[i + 1], data[i + 2] = bg
            continue

        # Red blush / red accents -> blue. Keep very dark red outline-like pixels untouched.
        if red_to_blue and r >= 120 and r > g * 1.45 and r > b * 1.45 and max(g, b) < 140:
            # preserve rough brightness so anti-aliased red edges stay anti-aliased
            v = max(120, min(255, r))
            data[i], data[i + 1], data[i + 2] = (0, min(90, g + 30), v)
            continue

        if force_black and r <= bt and g <= bt and b <= bt:
            data[i], data[i + 1], data[i + 2] = (0, 0, 0)

    return Image.frombytes("RGB", rgb.size, bytes(data))

def maybe_rotate(img: Image.Image, rotate: int) -> Image.Image:
    rotate = rotate % 360
    if rotate == 0:
        return img
    if rotate == 90:
        return img.transpose(Image.Transpose.ROTATE_90)
    if rotate == 180:
        return img.transpose(Image.Transpose.ROTATE_180)
    if rotate == 270:
        return img.transpose(Image.Transpose.ROTATE_270)
    raise ValueError("--rotate must be one of 0, 90, 180, 270")

def apply_safe_margin(img: Image.Image, margin: int, bg: tuple[int, int, int] = (0, 0, 0)) -> Image.Image:
    margin = max(0, int(margin))
    if margin <= 0:
        return normalize_color_space(img, bg=bg)
    w, h = img.size
    inner_w = max(1, w - margin * 2)
    inner_h = max(1, h - margin * 2)
    out = Image.new("RGB", (w, h), bg)
    resized = normalize_color_space(img, bg=bg).resize((inner_w, inner_h), Image.Resampling.LANCZOS)
    out.paste(resized, (margin, margin))
    return out

def prepare_external_image(
    path: str | Path | Image.Image,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fit: str = "contain",
    bg: tuple[int, int, int] = (0, 0, 0),
    green_to_bg: bool = False,
    red_to_blue: bool = False,
    force_black: bool = False,
    black_threshold: int = 45,
    safe_margin: int = 0,
    rotate: int = 0,
    content_rotate: int = 0,
) -> Image.Image:
    """Load an image and make a full TURMO framebuffer.

    Do not send 200x400 or any partial size to the device. This always returns
    a full width x height RGB image; the picture is resized/padded inside it.
    """
    if isinstance(path, Image.Image):
        src = path.copy()
    else:
        src = Image.open(path)
    # Rotate the SOURCE image before fitting it into the framebuffer.
    # This keeps the final framebuffer size unchanged, which is important
    # for screens whose logical stride is 480x320. Do NOT use --rotate 90/270
    # for stride tests because it changes final image size.
    src = maybe_rotate(src, content_rotate)
    src = transform_image_colors(
        src,
        bg=bg,
        green_to_bg=green_to_bg,
        red_to_blue=red_to_blue,
        force_black=force_black,
        black_threshold=black_threshold,
    )
    frame = fit_to_screen(src, width, height, fit=fit, bg=bg)
    # Run cleanup again after resizing because LANCZOS can create near-black / near-red edges.
    frame = transform_image_colors(
        frame,
        bg=bg,
        green_to_bg=False,
        red_to_blue=red_to_blue,
        force_black=force_black,
        black_threshold=black_threshold,
    )
    frame = apply_safe_margin(frame, safe_margin, bg=bg)
    frame = maybe_rotate(frame, rotate)
    return normalize_color_space(frame, bg=bg)
