"""FrameSource adapters over the current renderer functions."""

from __future__ import annotations

from types import SimpleNamespace

from .base import PreparedFrame
from ..frame import make_frame
from ..gif import prepare_gif_frames


class DashboardSource:
    def __init__(self, args: SimpleNamespace, delay_ms: int = 1000) -> None:
        self.args = args
        self.delay_ms = delay_ms

    def next_frame(self) -> PreparedFrame:
        return PreparedFrame(make_frame(self.args), self.delay_ms)


class TestPatternSource:
    def __init__(self, args: SimpleNamespace) -> None:
        self.args = args

    def next_frame(self) -> PreparedFrame:
        return PreparedFrame(make_frame(self.args), 0)


class ImageSource:
    def __init__(self, args: SimpleNamespace, image_path: str) -> None:
        self.args = args
        self.image_path = image_path

    def next_frame(self) -> PreparedFrame:
        args = SimpleNamespace(**vars(self.args))
        args.image = self.image_path
        return PreparedFrame(make_frame(args), 0)


class GifSource:
    def __init__(self, path: str, settings: dict) -> None:
        self.frames = prepare_gif_frames(
            path,
            width=int(settings["width"]),
            height=int(settings["height"]),
            fit=settings["fit"],
            bg=settings["bg"],
            green_to_bg=bool(settings["green_to_bg"]),
            red_to_blue=bool(settings["red_to_blue"]),
            force_black=bool(settings["force_black"]),
            black_threshold=int(settings["black_threshold"]),
            safe_margin=int(settings["safe_margin"]),
            rotate=int(settings["rotate"]),
            content_rotate=int(settings["content_rotate"]),
            fps_limit=float(settings["gif_fps"]),
            max_frames=int(settings["gif_max_frames"]),
        )
        self.index = 0

    def next_frame(self) -> PreparedFrame:
        img, delay_ms = self.frames[self.index]
        self.index = (self.index + 1) % len(self.frames)
        return PreparedFrame(img, delay_ms)
