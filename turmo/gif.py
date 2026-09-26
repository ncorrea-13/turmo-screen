"""Animated GIF loading and preparation."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageSequence

from .constants import DEFAULT_HEIGHT, DEFAULT_WIDTH
from .image_ops import prepare_external_image

def get_gif_frame_delay_ms(frame: Image.Image, fps_limit: float = 0.0) -> int:
    """Return frame delay, optionally overridden by FPS limit."""
    if fps_limit and fps_limit > 0:
        return max(1, int(1000 / float(fps_limit)))
    delay = int(frame.info.get("duration", 100) or 100)
    # Some GIFs store 0/10ms delays that are too fast for this serial screen.
    return max(40, delay)

def prepare_gif_frames(
    path: str | Path,
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
    fps_limit: float = 8.0,
    max_frames: int = 300,
) -> list[tuple[Image.Image, int]]:
    """Load a GIF/APNG-like image into prepared full-frame RGB frames.

    Every returned frame is already width x height and safe to send to the device.
    This intentionally sends full frames for reliability. RevA partial-window GIFs
    can be added later after the base protocol is stable.
    """
    src = Image.open(path)
    frames: list[tuple[Image.Image, int]] = []
    max_frames = max(1, int(max_frames))

    # Pillow's iterator handles normal GIF frame advancement. We copy each frame
    # immediately because the iterator reuses internal image state.
    for i, frame in enumerate(ImageSequence.Iterator(src)):
        if i >= max_frames:
            break
        delay_ms = get_gif_frame_delay_ms(frame, fps_limit=fps_limit)
        prepared = prepare_external_image(
            frame.copy().convert("RGBA"),
            width=width,
            height=height,
            fit=fit,
            bg=bg,
            green_to_bg=green_to_bg,
            red_to_blue=red_to_blue,
            force_black=force_black,
            black_threshold=black_threshold,
            safe_margin=safe_margin,
            rotate=rotate,
            content_rotate=content_rotate,
        )
        frames.append((prepared, delay_ms))

    if not frames:
        raise ValueError(f"No frames found in GIF: {path}")
    return frames
