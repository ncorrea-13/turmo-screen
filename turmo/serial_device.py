"""Serial protocol wrapper for legacy TURMO and RevA/Turing-style screens."""

from __future__ import annotations

import time

from PIL import Image

from .codecs import encode_pixels, encode_solid_pixels
from .constants import DEFAULT_BAUD, DEFAULT_PIXEL_FORMAT, MAGIC_1, MAGIC_2, USB2_PACKET_LEN

class TurmoSerial:
    """Small wrapper around pyserial for the TURMO USB2 serial protocol."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD, timeout: float = 0.35) -> None:
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise SystemExit("Missing dependency: pyserial. Install with: pip install -r requirements.txt") from exc

        self.port = port
        self.baud = baud
        self.ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
            write_timeout=timeout,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
        )

    def close(self) -> None:
        self.ser.close()

    def _packet(self, cmd: int) -> bytearray:
        packet = bytearray(USB2_PACKET_LEN)
        packet[0] = cmd & 0xFF
        packet[1] = MAGIC_1
        packet[2] = MAGIC_2
        packet[6] = 1
        return packet

    def send_raw(self, data: bytes) -> None:
        # The Windows app writes large buffers in chunks around 40960 bytes.
        chunk = 40960
        for offset in range(0, len(data), chunk):
            self.ser.write(data[offset : offset + chunk])
            self.ser.flush()
            time.sleep(0.0015)

    def command(self, cmd: int, *, sleep: float = 0.02) -> None:
        self.send_raw(bytes(self._packet(cmd)))
        if sleep:
            time.sleep(sleep)

    def reset(self) -> None:
        self.command(0x01, sleep=0.03)

    def set_brightness(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        packet = self._packet(0x03)
        packet[10] = value
        self.send_raw(bytes(packet))
        time.sleep(0.02)


    # ------------------------------------------------------------------
    # RevA / Turing Smart Screen 3.5" protocol
    # ------------------------------------------------------------------
    # The official 3.5" Turing/UsbMonitor serial protocol does NOT use the
    # 0x13/0x17 raw frame-size commands. It sends a compact 6-byte command
    # with packed coordinates, then RGB565LE pixel data. The important command
    # for our drifting-framebuffer issue is DISPLAY_BITMAP (197): it defines
    # the destination window, so the device's internal write cursor is reset to
    # x0,y0 before every frame.

    CMD_REVA_RESET = 101
    CMD_REVA_CLEAR = 102
    CMD_REVA_TO_BLACK = 103
    CMD_REVA_SCREEN_OFF = 108
    CMD_REVA_SCREEN_ON = 109
    CMD_REVA_SET_BRIGHTNESS = 110
    CMD_REVA_SET_ORIENTATION = 121
    CMD_REVA_DISPLAY_BITMAP = 197
    CMD_REVA_HELLO = 69

    def pack_reva_command(self, cmd: int, x: int = 0, y: int = 0, ex: int = 0, ey: int = 0) -> bytes:
        """Pack RevA coordinates exactly like the Turing/UsbMonitor 3.5 protocol."""
        x = max(0, int(x)); y = max(0, int(y)); ex = max(0, int(ex)); ey = max(0, int(ey))
        b = bytearray(6)
        b[0] = (x >> 2) & 0xFF
        b[1] = (((x & 3) << 6) + (y >> 4)) & 0xFF
        b[2] = (((y & 15) << 4) + (ex >> 6)) & 0xFF
        b[3] = (((ex & 63) << 2) + (ey >> 8)) & 0xFF
        b[4] = ey & 0xFF
        b[5] = cmd & 0xFF
        return bytes(b)

    def send_reva_command(self, cmd: int, x: int = 0, y: int = 0, ex: int = 0, ey: int = 0, *, sleep: float = 0.01) -> None:
        self.ser.write(self.pack_reva_command(cmd, x, y, ex, ey))
        self.ser.flush()
        if sleep:
            time.sleep(sleep)

    def hello_reva(self) -> bytes:
        """Ask newer UsbMonitor revisions for model. Official Turing 3.5 may not answer."""
        self.ser.reset_input_buffer()
        self.ser.write(bytes([self.CMD_REVA_HELLO]) * 6)
        self.ser.flush()
        time.sleep(0.05)
        data = self.ser.read(6)
        self.ser.reset_input_buffer()
        return data

    def set_orientation_reva(self, width: int, height: int, orientation: int = 0) -> None:
        """Set screen orientation/window size for RevA. orientation=0 means portrait."""
        packet = bytearray(16)
        # x/y/ex/ey all zero, command at byte 5
        packet[5] = self.CMD_REVA_SET_ORIENTATION & 0xFF
        packet[6] = (int(orientation) + 100) & 0xFF
        packet[7] = (int(width) >> 8) & 0xFF
        packet[8] = int(width) & 0xFF
        packet[9] = (int(height) >> 8) & 0xFF
        packet[10] = int(height) & 0xFF
        self.ser.write(bytes(packet))
        self.ser.flush()
        time.sleep(0.02)

    def clear_reva(self, width: int, height: int) -> None:
        # The upstream implementation notes that orientation should be portrait before clear.
        self.set_orientation_reva(width, height, orientation=0)
        self.send_reva_command(self.CMD_REVA_CLEAR, 0, 0, 0, 0, sleep=0.08)
        self.set_orientation_reva(width, height, orientation=0)

    def set_brightness_reva(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        # RevA expects inverted absolute brightness: 0 brightest, 255 darkest.
        absolute = int(255 - ((value / 100) * 255))
        self.send_reva_command(self.CMD_REVA_SET_BRIGHTNESS, absolute, 0, 0, 0, sleep=0.02)

    def send_image_reva(
        self,
        img: Image.Image,
        *,
        pixel_format: str = "rgb565le",
        x_byte: int = 0,
        chunk_lines: int = 4,
        set_orientation: bool = True,
    ) -> bool:
        """Send a full frame with the real RevA DISPLAY_BITMAP window command.

        This is the mode that should fix the cursor drift/wrap: before pixels,
        it sends DISPLAY_BITMAP with x0,y0,x1,y1 so the device knows exactly
        where the next RGB565 stream belongs.
        """
        width, height = img.size
        if set_orientation:
            self.set_orientation_reva(width, height, orientation=0)

        raw = encode_pixels(img, pixel_format=pixel_format, x_byte=x_byte)
        self.send_reva_command(self.CMD_REVA_DISPLAY_BITMAP, 0, 0, width - 1, height - 1, sleep=0.005)

        # Upstream sends chunks of display_width*8 bytes. For RGB565LE this is 4 lines.
        chunk = max(2, int(width) * 2 * max(1, int(chunk_lines)))
        for offset in range(0, len(raw), chunk):
            self.ser.write(raw[offset:offset + chunk])
            self.ser.flush()
            time.sleep(0.001)
        time.sleep(0.01)
        return True

    def send_frame_size(self, raw_len: int) -> None:
        # Cmd 0x13, bytes 6..9 contain big-endian raw frame byte length.
        packet = bytearray(USB2_PACKET_LEN)
        packet[0] = 0x13
        packet[1] = MAGIC_1
        packet[2] = MAGIC_2
        packet[6] = (raw_len >> 24) & 0xFF
        packet[7] = (raw_len >> 16) & 0xFF
        packet[8] = (raw_len >> 8) & 0xFF
        packet[9] = raw_len & 0xFF
        self.send_raw(bytes(packet))
        time.sleep(0.02)

    def begin_render(self, strict_ack: bool = False) -> bool:
        # Cmd 0x17. Some revisions ACK with 0x18 CF EF 01, some do not ACK.
        self.command(0x17, sleep=0.02)
        ack = self.ser.read(1024)
        ok = len(ack) >= 4 and ack[0] == 0x18 and ack[1] == MAGIC_1 and ack[2] == MAGIC_2 and ack[3] == 1
        if strict_ack and not ok:
            raise RuntimeError(f"Device did not return render ACK; got {ack[:16].hex(' ')}")
        return ok

    def send_image(
        self,
        img: Image.Image,
        *,
        pixel_format: str = DEFAULT_PIXEL_FORMAT,
        x_byte: int = 0,
        strict_ack: bool = False,
        reset_before_frame: bool = False,
        raw_prefix_pixels: int = 0,
        raw_tail_pixels: int = 0,
        pad_color: tuple[int, int, int] = (0, 0, 0),
    ) -> bool:
        # IMPORTANT: img must already be the full screen size. Sending smaller frames
        # makes the device continue drawing from the previous framebuffer position.
        if reset_before_frame:
            self.reset()
        raw = encode_pixels(img, pixel_format=pixel_format, x_byte=x_byte)
        if raw_prefix_pixels:
            raw = encode_solid_pixels(raw_prefix_pixels, color=pad_color, pixel_format=pixel_format, x_byte=x_byte) + raw
        if raw_tail_pixels:
            raw = raw + encode_solid_pixels(raw_tail_pixels, color=pad_color, pixel_format=pixel_format, x_byte=x_byte)
        self.send_frame_size(len(raw))
        ack = self.begin_render(strict_ack=strict_ack)
        self.send_raw(raw)
        return ack
