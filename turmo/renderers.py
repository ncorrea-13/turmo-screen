"""Built-in framebuffer renderers: dashboard and test pattern."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps

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

def _level_color(pct) -> tuple[int, int, int]:
    if not isinstance(pct, (int, float)):
        return (70, 80, 100)
    if pct >= 85:
        return (220, 70, 70)
    if pct >= 65:
        return (230, 190, 60)
    return (70, 140, 255)

def _fleet_base(width: int, height: int, bg_image: Optional[str]) -> Image.Image:
    if not bg_image:
        return Image.new("RGB", (width, height), (7, 10, 18))
    photo = ImageOps.fit(Image.open(bg_image).convert("RGB"), (width, height), Image.Resampling.LANCZOS)
    return Image.blend(photo, Image.new("RGB", (width, height), (0, 0, 0)), 0.55)  # dim so text stays readable

def render_fleet_dashboard(width: int, height: int, title: str = "REALMS", bg_image: Optional[str] = None) -> Image.Image:
    hosts = sorted(fetch_fleet_hosts(), key=lambda h: h.get("id", ""))
    base = _fleet_base(width, height, bg_image)
    card_alpha = 170 if bg_image else 255
    card_fill = (16, 23, 38, card_alpha)
    outline = (48, 70, 110, 255)

    unit = min(width, height * 2 // 3)  # fonts follow the short side so landscape stays compact
    title_font = safe_font(max(13, unit // 26), bold=True)
    name_font = safe_font(max(13, unit // 22), bold=True)
    small_font = safe_font(max(10, unit // 32))

    header_bottom = 38
    top = header_bottom + 8
    # Card content: name row + bars (+ optional third text line when there is room).
    compact_h = 6 + name_font.size + 6 + small_font.size + 5 + 6 + 6
    full_h = compact_h + small_font.size + 7
    row_h = min(max(compact_h + 6, (height - top - 6) // max(1, len(hosts))), 120)
    compact = row_h - 6 < full_h

    # Pass 1: translucent cards on an overlay, so a background image shows through.
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((12, 8, width - 12, header_bottom), radius=12, fill=card_fill, outline=outline, width=2)
    for i in range(len(hosts)):
        y = top + i * row_h
        od.rounded_rectangle((16, y, width - 16, y + row_h - 6), radius=10, fill=card_fill, outline=outline, width=2)
    img = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((20, 12), title, font=title_font, fill=(245, 248, 255))
    if not hosts:
        draw.text((26, header_bottom + 16), "No hosts (hub unreachable)", font=small_font, fill=(200, 120, 120))
        return img
    online = sum(1 for h in hosts if h.get("state") == "online")
    count = f"{online}/{len(hosts)}"
    count_color = STATE_COLORS["online"] if online == len(hosts) else STATE_COLORS["stale"] if online else STATE_COLORS["offline"]
    pill_w = int(draw.textlength(count, font=title_font)) + 22
    pill = (width - 18 - pill_w, 12, width - 18, header_bottom - 4)
    tint = tuple(int(16 + (c - 16) * 0.22) for c in count_color)
    draw.rounded_rectangle(pill, radius=(pill[3] - pill[1]) // 2, fill=tint, outline=count_color, width=1)
    draw.text(((pill[0] + pill[2]) // 2, (pill[1] + pill[3]) // 2), count, font=title_font, fill=count_color, anchor="mm")

    # Pass 2: content.
    for i, host in enumerate(hosts):
        y = top + i * row_h
        state = host.get("state", "unknown")
        color = STATE_COLORS.get(state, (120, 130, 150))
        metrics = host.get("metrics") or {}
        dim = state == "offline"
        name_fill = (120, 130, 150) if dim else (235, 240, 255)

        draw.ellipse((26, y + 12, 36, y + 22), fill=color)
        draw.text((42, y + 4), str(host.get("id", "?")), font=name_font, fill=name_fill)
        up = humanize_uptime(metrics.get("host.uptime"))
        temp = metrics.get("temp.pkg")
        load = metrics.get("cpu.load")
        latency = metrics.get("net.latency")
        temp_s = f"{temp:.0f}°C" if isinstance(temp, (int, float)) else "--"
        load_s = f"{load:.2f}" if isinstance(load, (int, float)) else "--"
        lat_s = f"{latency:.0f}ms" if isinstance(latency, (int, float)) else "--"
        extras = f"{temp_s}  LOAD {load_s}  NET {lat_s}"
        right = f"{extras}   {up}" if compact else up
        draw.text((width - 26 - draw.textlength(right, font=small_font), y + 6 + (name_font.size - small_font.size)), right, font=small_font, fill=(140, 160, 190))

        bars = [("CPU", metrics.get("cpu.util")), ("MEM", metrics.get("mem.used")), ("DSK", metrics.get("disk.used"))]
        x0, gap = 26, 8
        col_w = (width - 26 - x0 - gap * 2) // 3
        label_y = y + 6 + name_font.size + 6
        bar_y = label_y + small_font.size + 5
        for j, (label, value) in enumerate(bars):
            cx = x0 + j * (col_w + gap)
            draw.text((cx, label_y), f"{label} {_fmt_pct(value)}", font=small_font, fill=(190, 210, 240))
            draw.rounded_rectangle((cx, bar_y, cx + col_w, bar_y + 6), radius=3, fill=(30, 40, 60))
            if isinstance(value, (int, float)):
                fill_w = int(col_w * max(0.0, min(100.0, value)) / 100)
                if fill_w >= 3:
                    draw.rounded_rectangle((cx, bar_y, cx + fill_w, bar_y + 6), radius=3, fill=_level_color(value))

        if not compact:
            draw.text((26, bar_y + 6 + 7), extras, font=small_font, fill=(140, 160, 190))

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
