"""Compatibility façade used by old scripts and GUI.

New code should import from the specific modules, but this keeps the old
`import turmo_lite as core` style working through the wrapper file.
"""

from .codecs import encode_pixels, encode_solid_pixels
from .config import parse_bg
from .constants import *
from .frame import make_frame
from .gif import get_gif_frame_delay_ms, prepare_gif_frames
from .image_ops import (
    apply_safe_margin,
    fit_to_screen,
    maybe_rotate,
    normalize_color_space,
    prepare_external_image,
    roll_framebuffer,
    transform_image_colors,
)
from .metrics import collect_metrics, first_cpu_temp, nvidia_stats
from .models import Metrics
from .ports import find_candidate_ports, print_ports
from .renderers import draw_bar, render_dashboard, render_test_pattern, safe_font
from .serial_device import TurmoSerial

__all__ = [name for name in globals() if not name.startswith("_")]
