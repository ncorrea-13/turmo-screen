"""Built-in framebuffer renderers: dashboard and test pattern."""

from __future__ import annotations

import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .metrics import collect_metrics, fetch_fleet_hosts

STATE_COLORS = {
    "online": (70, 210, 130),
    "stale": (230, 190, 60),
    "offline": (220, 70, 70),
}

def safe_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for name in names:
        if os.path.exists(name):
            return ImageFont.truetype(name, size=size)
    return ImageFont.load_default()

def draw_bar(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], pct: float, label: str, value: str) -> None:
    x1, y1, x2, y2 = xy
    pct = max(0.0, min(100.0, pct))
    draw.rounded_rectangle(xy, radius=8, outline=(80, 100, 130), width=2, fill=(17, 24, 36))
    fill_w = int((x2 - x1 - 4) * pct / 100)
    draw.rounded_rectangle((x1 + 2, y1 + 2, x1 + 2 + fill_w, y2 - 2), radius=6, fill=(70, 140, 255))
    font = safe_font(16, bold=True)
    small = safe_font(13)
    draw.text((x1 + 10, y1 + 6), label, font=font, fill=(235, 240, 255))
    tw = draw.textlength(value, font=small)
    draw.text((x2 - tw - 10, y1 + 8), value, font=small, fill=(220, 230, 245))

def render_dashboard(width: int, height: int, title: str = "TURMO Linux") -> Image.Image:
    m = collect_metrics()
    img = Image.new("RGB", (width, height), (7, 10, 18))
    draw = ImageDraw.Draw(img)

    title_font = safe_font(max(18, width // 14), bold=True)
    mid_font = safe_font(max(14, width // 20), bold=True)
    small_font = safe_font(max(11, width // 28))
    tiny_font = safe_font(max(10, width // 32))

    draw.rounded_rectangle((12, 12, width - 12, 82), radius=18, fill=(16, 23, 38), outline=(48, 70, 110), width=2)
    draw.text((26, 24), title, font=title_font, fill=(245, 248, 255))
    now = datetime.now()
    draw.text((26, 54), now.strftime("%H:%M:%S  %d.%m.%Y"), font=small_font, fill=(170, 190, 220))

    y = 102
    gap = 52
    draw_bar(draw, (16, y, width - 16, y + 40), m.cpu, "CPU", f"{m.cpu:.0f}%")
    y += gap
    draw_bar(draw, (16, y, width - 16, y + 40), m.ram, "RAM", f"{m.ram:.0f}%")
    y += gap
    draw_bar(draw, (16, y, width - 16, y + 40), m.disk, "DISK /", f"{m.disk:.0f}%")
    y += gap
    gpu_pct = m.gpu if m.gpu is not None else 0
    draw_bar(draw, (16, y, width - 16, y + 40), gpu_pct, "GPU", "N/A" if m.gpu is None else f"{m.gpu:.0f}%")

    card_top = height - 138
    draw.rounded_rectangle((16, card_top, width - 16, height - 18), radius=16, fill=(16, 23, 38), outline=(48, 70, 110), width=2)

    cpu_temp = "N/A" if m.cpu_temp is None else f"{m.cpu_temp:.0f}°C"
    gpu_temp = "N/A" if m.gpu_temp is None else f"{m.gpu_temp:.0f}°C"
    draw.text((30, card_top + 18), "TEMP", font=mid_font, fill=(235, 240, 255))
    draw.text((30, card_top + 48), f"CPU {cpu_temp}", font=small_font, fill=(190, 210, 240))
    draw.text((30, card_top + 72), f"GPU {gpu_temp}", font=small_font, fill=(190, 210, 240))

    right_x = width // 2 + 8
    draw.text((right_x, card_top + 18), "NET", font=mid_font, fill=(235, 240, 255))
    draw.text((right_x, card_top + 48), f"↓ {m.net_down_kb:.0f} KB/s", font=tiny_font, fill=(190, 210, 240))
    draw.text((right_x, card_top + 72), f"↑ {m.net_up_kb:.0f} KB/s", font=tiny_font, fill=(190, 210, 240))

    return img

def humanize_uptime(seconds) -> str:
    if not isinstance(seconds, (int, float)):
        return "--"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def _fmt_pct(value) -> str:
    return f"{value:.0f}%" if isinstance(value, (int, float)) else "--"

def render_fleet_dashboard(width: int, height: int, title: str = "Homelab Fleet") -> Image.Image:
    hosts = sorted(fetch_fleet_hosts(), key=lambda h: h.get("id", ""))
    img = Image.new("RGB", (width, height), (7, 10, 18))
    draw = ImageDraw.Draw(img)

    title_font = safe_font(max(13, width // 26), bold=True)
    name_font = safe_font(max(13, width // 22), bold=True)
    small_font = safe_font(max(10, width // 32))

    header_bottom = 38
    draw.rounded_rectangle((12, 8, width - 12, header_bottom), radius=12, fill=(16, 23, 38), outline=(48, 70, 110), width=2)
    draw.text((20, 12), title, font=title_font, fill=(245, 248, 255))

    if not hosts:
        draw.text((26, header_bottom + 16), "No hosts (hub unreachable)", font=small_font, fill=(200, 120, 120))
        return img

    top = header_bottom + 8
    row_min = 12 + name_font.size + small_font.size * 2 + 10
    row_h = max(row_min, (height - top - 6) // len(hosts))
    y = top
    for host in hosts:
        state = host.get("state", "unknown")
        color = STATE_COLORS.get(state, (120, 130, 150))
        metrics = host.get("metrics") or {}

        draw.rounded_rectangle((16, y, width - 16, y + row_h - 6), radius=10, fill=(16, 23, 38), outline=(48, 70, 110), width=2)
        dot_y = y + 14
        draw.ellipse((26, dot_y, 36, dot_y + 10), fill=color)
        draw.text((42, y + 6), str(host.get("id", "?")), font=name_font, fill=(235, 240, 255))

        line2_y = y + 6 + name_font.size + 2
        stat = f"CPU {_fmt_pct(metrics.get('cpu.util'))}  MEM {_fmt_pct(metrics.get('mem.used'))}  DISK {_fmt_pct(metrics.get('disk.used'))}"
        draw.text((42, line2_y), stat, font=small_font, fill=(190, 210, 240))

        temp = metrics.get("temp.pkg")
        load = metrics.get("cpu.load")
        latency = metrics.get("net.latency")
        temp_s = f"{temp:.0f}°C" if isinstance(temp, (int, float)) else "--"
        load_s = f"{load:.2f}" if isinstance(load, (int, float)) else "--"
        lat_s = f"{latency:.0f}ms" if isinstance(latency, (int, float)) else "--"
        line3_y = line2_y + small_font.size + 3
        extra = f"UP {humanize_uptime(metrics.get('host.uptime'))}  TEMP {temp_s}  LOAD {load_s}  NET {lat_s}"
        draw.text((42, line3_y), extra, font=small_font, fill=(140, 160, 190))

        y += row_h

    return img

def render_test_pattern(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = [
        ((255, 0, 0), "RED"),
        ((0, 255, 0), "GREEN"),
        ((0, 0, 255), "BLUE"),
        ((255, 255, 255), "WHITE"),
        ((0, 0, 0), "BLACK"),
    ]
    stripe_h = max(1, height // len(colors))
    font = safe_font(max(16, width // 12), bold=True)
    for i, (color, label) in enumerate(colors):
        y1 = i * stripe_h
        y2 = height if i == len(colors) - 1 else (i + 1) * stripe_h
        draw.rectangle((0, y1, width, y2), fill=color)
        text_fill = (255, 255, 255) if label == "BLACK" else (0, 0, 0)
        draw.text((14, y1 + 14), label, font=font, fill=text_fill)
    draw.rectangle((0, 0, width - 1, height - 1), outline=(255, 255, 255), width=4)
    draw.line((0, 0, width - 1, height - 1), fill=(255, 255, 255), width=2)
    draw.line((width - 1, 0, 0, height - 1), fill=(255, 255, 255), width=2)
    return img
