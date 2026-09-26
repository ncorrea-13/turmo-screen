"""Command-line entry point for TURMO Linux."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable, Optional

from PIL import Image

from .codecs import encode_pixels
from .config import parse_bg
from .constants import DEFAULT_BAUD, DEFAULT_HEIGHT, DEFAULT_PIXEL_FORMAT, DEFAULT_WIDTH, PIXEL_FORMATS, REVA_ORIENTATIONS, RGB565_FORMATS
from .frame import make_frame
from .gif import prepare_gif_frames
from .ports import print_ports
from .serial_device import TurmoSerial

def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Simple non-commercial TURMO Linux dashboard/image sender")
    parser.add_argument("--list", action="store_true", help="list serial ports and exit")
    parser.add_argument("--port", default="/dev/ttyACM0", help="serial port, for example /dev/ttyACM0 or /dev/serial/by-id/...")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="baud rate; 4000000 worked in testing, RevA often also ignores/accepts 115200")
    parser.add_argument("--protocol", choices=["reva", "legacy"], default="reva", help="reva sends real DISPLAY_BITMAP window command; legacy uses old raw 0x13/0x17 mode")
    parser.add_argument("--reva-no-orientation", action="store_true", help="do not send SET_ORIENTATION before each RevA frame")
    parser.add_argument("--orientation", choices=list(REVA_ORIENTATIONS), default="portrait", help="RevA screen orientation; pair --orientation landscape with --width 480 --height 320")
    parser.add_argument("--reva-chunk-lines", type=int, default=4, help="RevA image data chunk size in screen lines, default 4")
    parser.add_argument("--hello", action="store_true", help="send RevA HELLO and print 6-byte response, if any")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270], help="rotate final framebuffer; avoid 90/270 when testing stride")
    parser.add_argument("--content-rotate", type=int, default=0, choices=[0, 90, 180, 270], help="rotate source image before fitting; final framebuffer size is preserved")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between frames")
    parser.add_argument("--title", default="TURMO Linux")
    parser.add_argument("--brightness", type=int, help="set brightness 0..100 before sending frames")
    parser.add_argument("--pixel-format", choices=PIXEL_FORMATS, default=DEFAULT_PIXEL_FORMAT)
    parser.add_argument("--pixel-order", choices=["bgra", "rgba"], help="old alias for --pixel-format")
    parser.add_argument("--x-byte", type=int, default=0, help="value for X byte in rgbx/bgrx/xrgb/xbgr, usually 0")
    parser.add_argument("--safe-margin", type=int, default=0, help="shrink content inside a black margin, for example 20 or 40")
    parser.add_argument("--roll-x", type=int, default=0, help="circularly shift final framebuffer horizontally in pixels; calibration only")
    parser.add_argument("--roll-y", type=int, default=0, help="circularly shift final framebuffer vertically in pixels; calibration only")
    parser.add_argument("--raw-prefix-pixels", type=int, default=0, help="send this many black pixels before the real frame; calibration only")
    parser.add_argument("--raw-tail-pixels", type=int, default=0, help="send this many black pixels after the real frame to stabilize cursor drift; calibration only")
    parser.add_argument("--test-pattern", action="store_true", help="send color bars instead of dashboard")
    parser.add_argument("--fleet", action="store_true", help="show Heimdall fleet status instead of local dashboard; reads HEIMDALL_HUB/HEIMDALL_TOKEN env vars")
    parser.add_argument("--image", help="send PNG/JPG/WebP image; it will be normalized, resized and padded into the full frame")
    parser.add_argument("--gif", help="play animated GIF; frames are normalized/resized/padded into the full frame")
    parser.add_argument("--gif-fps", type=float, default=8.0, help="override GIF speed, default 8 FPS; use 0 for original delays")
    parser.add_argument("--gif-loop", action="store_true", help="loop GIF forever; otherwise play one cycle and exit")
    parser.add_argument("--gif-max-frames", type=int, default=300, help="limit decoded frames to avoid huge RAM use, default 300")
    parser.add_argument("--fit", choices=["contain", "cover", "stretch"], default="contain", help="how --image is placed inside the screen")
    parser.add_argument("--bg", type=parse_bg, default=(0, 0, 0), help="background for PNG alpha/padding: black, white, gray, or #RRGGBB")
    parser.add_argument("--pink-bg", action="store_true", help="shortcut for --bg #e15cff; useful for the uploaded cat picture")
    parser.add_argument("--green-to-bg", action="store_true", help="replace green-ish background pixels with --bg / --pink-bg")
    parser.add_argument("--red-to-blue", action="store_true", help="replace red accents with blue before sending/saving")
    parser.add_argument("--force-black", action="store_true", help="snap near-black outline pixels to true black")
    parser.add_argument("--black-threshold", type=int, default=45, help="threshold for --force-black, default 45")
    parser.add_argument("--save-prepared", metavar="PNG", help="save prepared full-frame image before sending")
    parser.add_argument("--prepare-only", action="store_true", help="only save/render prepared image and do not open serial port")
    parser.add_argument("--clear", action="store_true", help="send a full black frame before the real frame")
    parser.add_argument("--reset-before-frame", action="store_true", help="send reset command before each frame; may help if framebuffer position gets stuck")
    parser.add_argument("--strict-ack", action="store_true", help="fail if the device does not ACK render command")
    parser.add_argument("--once", action="store_true", help="send one frame and exit")
    parser.add_argument("--dry-run", metavar="PNG", help="render one frame into PNG instead of sending to device")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.pink_bg:
        args.bg = (225, 92, 255)

    if args.pixel_order and args.pixel_format == DEFAULT_PIXEL_FORMAT:
        args.pixel_format = args.pixel_order

    if args.list:
        print_ports()
        return 0

    gif_frames: list[tuple[Image.Image, int]] | None = None
    if args.gif:
        gif_frames = prepare_gif_frames(
            args.gif,
            width=args.width,
            height=args.height,
            fit=args.fit,
            bg=args.bg,
            green_to_bg=args.green_to_bg,
            red_to_blue=args.red_to_blue,
            force_black=args.force_black,
            black_threshold=args.black_threshold,
            safe_margin=args.safe_margin,
            rotate=args.rotate,
            content_rotate=args.content_rotate,
            fps_limit=args.gif_fps,
            max_frames=args.gif_max_frames,
        )
        img = gif_frames[0][0]
    else:
        img = make_frame(args)

    if args.dry_run:
        img.save(args.dry_run)
        raw = encode_pixels(img, pixel_format=args.pixel_format, x_byte=args.x_byte)
        if gif_frames:
            print(f"Rendered GIF first-frame preview: {args.dry_run} ({len(gif_frames)} frames loaded)")
        else:
            print(f"Rendered preview: {args.dry_run}")
        print(f"Frame: {img.size[0]}x{img.size[1]}, format={args.pixel_format}, protocol={args.protocol}, bytes={len(raw)}")
        return 0

    if args.save_prepared:
        img.save(args.save_prepared)
        print(f"Saved prepared frame: {args.save_prepared} ({img.size[0]}x{img.size[1]})")

    if args.prepare_only:
        if not args.save_prepared:
            print("Nothing sent. Use --save-prepared OUT.png or --dry-run OUT.png with --prepare-only.")
        return 0

    dev = TurmoSerial(args.port, baud=args.baud)
    try:
        if args.hello:
            response = dev.hello_reva()
            print("HELLO response:", response.hex(" ") if response else "<no response>")

        if args.brightness is not None:
            if args.protocol == "reva":
                dev.set_brightness_reva(args.brightness)
            else:
                dev.set_brightness(args.brightness)

        orientation_value = REVA_ORIENTATIONS[args.orientation]

        if args.clear:
            if args.protocol == "reva":
                dev.clear_reva(orientation_value)
            else:
                black = Image.new("RGB", img.size, (0, 0, 0))
                dev.send_image(black, pixel_format=args.pixel_format, x_byte=args.x_byte, strict_ack=False, reset_before_frame=args.reset_before_frame, raw_prefix_pixels=0, raw_tail_pixels=args.raw_tail_pixels, pad_color=args.bg)
            time.sleep(0.05)

        def send_one_frame(frame_img: Image.Image) -> None:
            if args.protocol == "reva":
                if args.pixel_format not in RGB565_FORMATS:
                    print("warning: RevA usually expects rgb565le; current format is", args.pixel_format, file=sys.stderr)
                dev.send_image_reva(
                    frame_img,
                    pixel_format=args.pixel_format,
                    x_byte=args.x_byte,
                    chunk_lines=args.reva_chunk_lines,
                    set_orientation=not args.reva_no_orientation,
                    orientation=orientation_value,
                )
            else:
                ack = dev.send_image(
                    frame_img,
                    pixel_format=args.pixel_format,
                    x_byte=args.x_byte,
                    strict_ack=args.strict_ack,
                    reset_before_frame=args.reset_before_frame,
                    raw_prefix_pixels=args.raw_prefix_pixels,
                    raw_tail_pixels=args.raw_tail_pixels,
                    pad_color=args.bg,
                )
                if not ack:
                    print("warning: no render ACK from device; frame was still sent", file=sys.stderr)

        if gif_frames:
            print(f"Playing GIF: {len(gif_frames)} frames, fps_override={args.gif_fps}, loop={args.gif_loop}")
            while True:
                for frame_img, delay_ms in gif_frames:
                    send_one_frame(frame_img)
                    time.sleep(max(0.04, delay_ms / 1000.0))
                if not args.gif_loop:
                    break
        else:
            while True:
                frame_img = make_frame(args)
                send_one_frame(frame_img)
                if args.once:
                    break
                time.sleep(max(0.05, args.interval))
    finally:
        dev.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
