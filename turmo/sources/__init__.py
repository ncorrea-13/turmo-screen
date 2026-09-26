"""Frame source abstractions.

Screen streaming should be added as another FrameSource instead of being
hardcoded into CLI/GUI sender loops.
"""

from .base import FrameSource, PreparedFrame
from .builtins import DashboardSource, GifSource, ImageSource, TestPatternSource

__all__ = [
    "FrameSource",
    "PreparedFrame",
    "DashboardSource",
    "GifSource",
    "ImageSource",
    "TestPatternSource",
]
