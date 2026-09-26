"""Minimal source interface for future dashboard/image/GIF/screen streams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class PreparedFrame:
    image: Image.Image
    delay_ms: int = 0


class FrameSource(Protocol):
    def next_frame(self) -> PreparedFrame:
        """Return the next full-size RGB framebuffer."""
        ...
