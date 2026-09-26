"""Placeholder for future screen capture.

Keep capture logic here later. The sender should only consume prepared
full-frame PIL images and should not know whether they came from a GIF,
dashboard, static image or desktop capture.
"""

from __future__ import annotations


class ScreenCaptureSource:
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "Screen capture is intentionally not implemented yet. "
            "Add it here later, for example through mss/pipewire/x11 capture, "
            "then feed frames through turmo.image_ops.prepare_external_image."
        )
