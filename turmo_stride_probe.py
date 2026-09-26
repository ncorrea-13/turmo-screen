#!/usr/bin/env python3
"""TURMO raw stride probe.

This sends raw RGBX pixels directly. It is used to find the logical scanline
width/stride of the USB display. The correct candidate is the one where the
vertical white/black/magenta/cyan lines are straight and do not wrap diagonally.
"""
from __future__ import annotations
import argparse, time, sys

MAGIC_1=0xCF
MAGIC_2=0xEF
PACKET_LEN=250
DEFAULT_PORT='/dev/ttyACM0'
DEFAULT_BAUD=4_000_000

def packet(cmd:int)->bytearray:
    p=bytearray(PACKET_LEN)
    p[0]=cmd & 0xFF
    p[1]=MAGIC_1
    p[2]=MAGIC_2
    p[6]=1
    return p

class Dev:
    def __init__(self, port, baud):
        import serial
        self.ser=serial.Serial(port=port, baudrate=baud, bytesize=8, parity='N', stopbits=1,
                               timeout=0.25, write_timeout=0.5, rtscts=False, dsrdtr=False, xonxoff=False)
    def raw(self, data:bytes):
        for i in range(0, len(data), 40960):
            self.ser.write(data[i:i+40960]); self.ser.flush(); time.sleep(0.0015)
    def cmd(self, cmd:int, sleep=0.02):
        self.raw(bytes(packet(cmd)))
        if sleep: time.sleep(sleep)
    def reset(self):
        self.cmd(0x01, sleep=0.06)
    def frame_size(self, n:int):
        p=bytearray(PACKET_LEN)
        p[0]=0x13; p[1]=MAGIC_1; p[2]=MAGIC_2
        p[6]=(n>>24)&255; p[7]=(n>>16)&255; p[8]=(n>>8)&255; p[9]=n&255
        self.raw(bytes(p)); time.sleep(0.03)
    def begin(self):
        self.cmd(0x17, sleep=0.03)
        _=self.ser.read(1024)
    def close(self):
        self.ser.close()

def rgbx(r,g,b,x=0): return bytes((r&255,g&255,b&255,x&255))

def make_probe(candidate_stride:int, total_pixels:int, xbyte:int=0)->bytes:
    W=max(1, candidate_stride)
    out=bytearray(total_pixels*4)
    # Make a pattern in the RAW STREAM as if the screen width were W.
    # If W equals the real hardware stride, vertical stripes will be straight.
    colors=[(255,0,255), (0,255,255), (255,255,255), (0,0,0)]
    j=0
    for idx in range(total_pixels):
        x=idx % W
        y=idx // W
        # background: dark blue gradient-ish so wraps are visible
        r=10
        g=(20 + (y*3) % 80)
        b=(50 + (x*2) % 120)
        # left/right borders for candidate stride
        if x < 4 or x >= W-4:
            r,g,b=(255,255,255)
        # vertical guide lines
        elif x % 40 < 3:
            r,g,b=colors[(x//40) % len(colors)]
        # horizontal guide lines
        elif y % 40 < 3:
            r,g,b=(255,200,0)
        out[j]=r; out[j+1]=g; out[j+2]=b; out[j+3]=xbyte&255
        j+=4
    return bytes(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--port', default=DEFAULT_PORT)
    ap.add_argument('--baud', type=int, default=DEFAULT_BAUD)
    ap.add_argument('--stride', type=int, required=True, help='candidate logical width/stride, e.g. 240, 320, 480')
    ap.add_argument('--pixels', type=int, default=320*480, help='total pixels to send; default 153600')
    ap.add_argument('--x-byte', type=int, default=0)
    ap.add_argument('--no-reset', action='store_true')
    args=ap.parse_args()
    raw=make_probe(args.stride, args.pixels, args.x_byte)
    print(f'sending stride probe: candidate={args.stride}, pixels={args.pixels}, bytes={len(raw)}')
    dev=Dev(args.port, args.baud)
    try:
        if not args.no_reset:
            dev.reset()
        dev.frame_size(len(raw))
        dev.begin()
        dev.raw(raw)
    finally:
        dev.close()
    return 0

if __name__=='__main__':
    raise SystemExit(main())
