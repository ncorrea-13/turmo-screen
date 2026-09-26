"""Frame factory that selects image, test-pattern or dashboard rendering."""

from __future__ import annotations

import argparse

from PIL import Image

from .image_ops import apply_safe_margin, maybe_rotate, normalize_color_space, prepare_external_image, roll_framebuffer
from .renderers import render_dashboard, render_test_pattern

def make_frame(args: argparse.Namespace) -> Image.Image:
    bg = args.bg
    if args.image:
        # External images need the full pipeline: palette/alpha -> RGB, optional color
        # replacement, fit into full framebuffer, margin, rotation.
        img = prepare_external_image(
            args.image,
            width=args.width,
            height=args.height,
            fit=args.fit,
            bg=bg,
            green_to_bg=args.green_to_bg,
            red_to_blue=args.red_to_blue,
            force_black=args.force_black,
            black_threshold=args.black_threshold,
            safe_margin=args.safe_margin,
            rotate=args.rotate,
            content_rotate=args.content_rotate,
        )
        return roll_framebuffer(img, args.roll_x, args.roll_y)
    elif args.test_pattern:
        img = render_test_pattern(args.width, args.height)
    else:
        img = render_dashboard(args.width, args.height, args.title)

    img = apply_safe_margin(img, args.safe_margin, bg=bg)
    img = maybe_rotate(img, args.rotate)
    img = roll_framebuffer(img, args.roll_x, args.roll_y)
    # Always return RGB, no palette/alpha surprises.
    return normalize_color_space(img, bg=bg)
