#!/usr/bin/env python3
"""
TURMO Linux UI GIF alpha

PySide6 window over turmo_lite.py with image, dashboard and animated GIF sending.
CLI core stays usable if the GUI breaks.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from PIL import Image

try:
    from PySide6.QtCore import Qt, QThread, Signal, QTimer
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSlider,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing GUI dependency: PySide6. Run ./install.sh") from exc

from . import core

APP_NAME = "TURMO Linux UI GIF alpha"
CONFIG_DIR = Path.home() / ".config" / "turmo-linux-ui"
CONFIG_PATH = CONFIG_DIR / "settings-gif-alpha.json"


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    rgba = core.normalize_color_space(img).convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if not value:
        return (0, 0, 0)
    if not value.startswith("#"):
        value = "#" + value
    if len(value) != 7:
        raise ValueError("Background must be #RRGGBB")
    return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(rgb)


class PreviewLabel(QLabel):
    def __init__(self) -> None:
        super().__init__("Preview")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(280, 380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background:#111827; color:#9ca3af; border:1px solid #374151; border-radius:8px;")
        self._pixmap: Optional[QPixmap] = None

    def set_pil(self, img: Image.Image) -> None:
        self._pixmap = pil_to_pixmap(img)
        self._rescale()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._pixmap is None:
            return
        self.setPixmap(self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


class SendWorker(QThread):
    status = Signal(str)
    failed = Signal(str)
    finished_ok = Signal(str)

    def __init__(self, settings: dict, mode: str, image_path: Optional[str] = None) -> None:
        super().__init__()
        self.settings = dict(settings)
        self.mode = mode
        self.image_path = image_path
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def _make_args(self, mode: str, image_path: Optional[str] = None) -> SimpleNamespace:
        s = self.settings
        return SimpleNamespace(
            image=image_path if mode == "image" else None,
            test_pattern=mode == "test",
            width=int(s["width"]),
            height=int(s["height"]),
            fit=s["fit"],
            bg=s["bg"],
            green_to_bg=bool(s["green_to_bg"]),
            red_to_blue=bool(s["red_to_blue"]),
            force_black=bool(s["force_black"]),
            black_threshold=int(s["black_threshold"]),
            safe_margin=int(s["safe_margin"]),
            rotate=int(s["rotate"]),
            content_rotate=int(s["content_rotate"]),
            roll_x=int(s["roll_x"]),
            roll_y=int(s["roll_y"]),
            title=s["title"],
        )

    def _send_one(self, dev: core.TurmoSerial, img: Image.Image) -> None:
        s = self.settings
        protocol = s["protocol"]
        pixel_format = s["pixel_format"]
        if protocol == "reva":
            dev.send_image_reva(
                img,
                pixel_format=pixel_format,
                x_byte=int(s["x_byte"]),
                chunk_lines=int(s["reva_chunk_lines"]),
                set_orientation=not bool(s["reva_no_orientation"]),
            )
        else:
            dev.send_image(
                img,
                pixel_format=pixel_format,
                x_byte=int(s["x_byte"]),
                strict_ack=False,
                reset_before_frame=bool(s["reset_before_frame"]),
                raw_prefix_pixels=int(s["raw_prefix_pixels"]),
                raw_tail_pixels=int(s["raw_tail_pixels"]),
                pad_color=s["bg"],
            )

    def run(self) -> None:  # noqa: C901
        dev = None
        try:
            s = self.settings
            self.status.emit(f"Opening {s['port']} at {s['baud']} baud...")
            dev = core.TurmoSerial(s["port"], baud=int(s["baud"]))

            brightness = int(s.get("brightness", -1))
            if brightness >= 0:
                if s["protocol"] == "reva":
                    dev.set_brightness_reva(brightness)
                else:
                    dev.set_brightness(brightness)

            if bool(s.get("clear", False)):
                if s["protocol"] == "reva":
                    dev.clear_reva(int(s["width"]), int(s["height"]))
                else:
                    black = Image.new("RGB", (int(s["width"]), int(s["height"])), s["bg"])
                    self._send_one(dev, black)

            if self.mode == "gif":
                if not self.image_path:
                    raise ValueError("Open a GIF first")
                frames = core.prepare_gif_frames(
                    self.image_path,
                    width=int(s["width"]),
                    height=int(s["height"]),
                    fit=s["fit"],
                    bg=s["bg"],
                    green_to_bg=bool(s["green_to_bg"]),
                    red_to_blue=bool(s["red_to_blue"]),
                    force_black=bool(s["force_black"]),
                    black_threshold=int(s["black_threshold"]),
                    safe_margin=int(s["safe_margin"]),
                    rotate=int(s["rotate"]),
                    content_rotate=int(s["content_rotate"]),
                    fps_limit=float(s["gif_fps"]),
                    max_frames=int(s["gif_max_frames"]),
                )
                self.status.emit(f"GIF loaded: {len(frames)} frames")
                cycle = 0
                while not self._stop:
                    cycle += 1
                    for i, (img, delay_ms) in enumerate(frames, start=1):
                        if self._stop:
                            break
                        self._send_one(dev, img)
                        self.status.emit(f"GIF cycle {cycle}, frame {i}/{len(frames)}, delay={delay_ms}ms")
                        self.msleep(max(40, int(delay_ms)))
                    if not bool(s["gif_loop"]):
                        break
                self.finished_ok.emit("GIF stopped" if self._stop else "GIF done")
                return

            sent = 0
            while not self._stop:
                img = core.make_frame(self._make_args(self.mode, self.image_path))
                self._send_one(dev, img)
                sent += 1
                self.status.emit(f"Sent frame {sent}: {img.size[0]}x{img.size[1]}, {s['protocol']}, {s['pixel_format']}")
                if self.mode in {"test", "image"}:
                    break
                self.msleep(max(50, int(float(s["interval"]) * 1000)))
            self.finished_ok.emit("Stopped" if self._stop else "Done")
        except Exception as exc:
            text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            if "Permission denied" in text or "Errno 13" in text:
                text += "\n\nTry:\n  sudo chmod a+rw /dev/ttyACM0\n\nPermanent fix:\n  sudo usermod -aG dialout $USER\n  sudo usermod -aG uucp $USER\n  reboot"
            self.failed.emit(text)
        finally:
            if dev is not None:
                try:
                    dev.close()
                except Exception:
                    pass


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1040, 720)
        self.worker: Optional[SendWorker] = None
        self.image_path: Optional[str] = None
        self.gif_path: Optional[str] = None
        self._build_ui()
        self.load_settings()
        self.refresh_ports()
        self.update_preview_dashboard()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        left = QVBoxLayout()
        main.addLayout(left, 0)
        self.preview = PreviewLabel()
        main.addWidget(self.preview, 1)

        device_box = QGroupBox("Device")
        device_form = QFormLayout(device_box)
        self.port_combo = QComboBox(); self.port_combo.setEditable(True)
        refresh_btn = QPushButton("Refresh"); refresh_btn.clicked.connect(self.refresh_ports)
        port_row = QHBoxLayout(); port_row.addWidget(self.port_combo, 1); port_row.addWidget(refresh_btn)
        device_form.addRow("Port", port_row)
        self.protocol_combo = QComboBox(); self.protocol_combo.addItems(["reva", "legacy"])
        self.baud_spin = QSpinBox(); self.baud_spin.setRange(9600, 6000000); self.baud_spin.setValue(4000000)
        self.pixel_combo = QComboBox(); self.pixel_combo.addItems(["rgb565le", "bgr565le", "rgbx", "bgrx", "rgba", "bgra", "rgb888", "bgr888"])
        self.width_spin = QSpinBox(); self.width_spin.setRange(1, 2000); self.width_spin.setValue(320)
        self.height_spin = QSpinBox(); self.height_spin.setRange(1, 2000); self.height_spin.setValue(480)
        size_row = QHBoxLayout(); size_row.addWidget(self.width_spin); size_row.addWidget(QLabel("×")); size_row.addWidget(self.height_spin)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal); self.brightness_slider.setRange(-1, 100); self.brightness_slider.setValue(-1)
        self.title_edit = QLineEdit("TURMO Linux")
        device_form.addRow("Protocol", self.protocol_combo)
        device_form.addRow("Baud", self.baud_spin)
        device_form.addRow("Pixel", self.pixel_combo)
        device_form.addRow("Size", size_row)
        device_form.addRow("Brightness (-1 skip)", self.brightness_slider)
        device_form.addRow("Dashboard title", self.title_edit)
        left.addWidget(device_box)

        image_box = QGroupBox("Image / GIF / Transform")
        grid = QGridLayout(image_box)
        self.open_btn = QPushButton("Open image"); self.open_btn.clicked.connect(self.open_image)
        self.open_gif_btn = QPushButton("Open GIF"); self.open_gif_btn.clicked.connect(self.open_gif)
        self.image_label = QLabel("No image/GIF"); self.image_label.setWordWrap(True)
        grid.addWidget(self.open_btn, 0, 0); grid.addWidget(self.open_gif_btn, 0, 1); grid.addWidget(self.image_label, 0, 2, 1, 2)
        self.fit_combo = QComboBox(); self.fit_combo.addItems(["contain", "cover", "stretch"])
        self.bg_edit = QLineEdit("#000000")
        self.pink_btn = QPushButton("Pink bg"); self.pink_btn.clicked.connect(lambda: self.bg_edit.setText("#e15cff"))
        grid.addWidget(QLabel("Fit"), 1, 0); grid.addWidget(self.fit_combo, 1, 1)
        grid.addWidget(QLabel("BG"), 2, 0); grid.addWidget(self.bg_edit, 2, 1); grid.addWidget(self.pink_btn, 2, 2)
        self.green_cb = QCheckBox("green → bg"); self.red_cb = QCheckBox("red → blue"); self.black_cb = QCheckBox("force black")
        self.green_cb.setChecked(True); self.red_cb.setChecked(True); self.black_cb.setChecked(True)
        grid.addWidget(self.green_cb, 3, 0); grid.addWidget(self.red_cb, 3, 1); grid.addWidget(self.black_cb, 3, 2)
        self.safe_margin_spin = QSpinBox(); self.safe_margin_spin.setRange(0, 240); self.safe_margin_spin.setValue(0)
        self.black_threshold_spin = QSpinBox(); self.black_threshold_spin.setRange(0, 255); self.black_threshold_spin.setValue(45)
        grid.addWidget(QLabel("Safe margin"), 4, 0); grid.addWidget(self.safe_margin_spin, 4, 1)
        grid.addWidget(QLabel("Black threshold"), 5, 0); grid.addWidget(self.black_threshold_spin, 5, 1)
        self.gif_fps_spin = QDoubleSpinBox(); self.gif_fps_spin.setRange(0.0, 30.0); self.gif_fps_spin.setDecimals(1); self.gif_fps_spin.setValue(8.0)
        self.gif_loop_cb = QCheckBox("loop GIF"); self.gif_loop_cb.setChecked(True)
        self.gif_max_spin = QSpinBox(); self.gif_max_spin.setRange(1, 2000); self.gif_max_spin.setValue(300)
        grid.addWidget(QLabel("GIF FPS (0 original)"), 6, 0); grid.addWidget(self.gif_fps_spin, 6, 1); grid.addWidget(self.gif_loop_cb, 6, 2)
        grid.addWidget(QLabel("GIF max frames"), 7, 0); grid.addWidget(self.gif_max_spin, 7, 1)
        left.addWidget(image_box)

        advanced_box = QGroupBox("Advanced / Calibration")
        adv = QGridLayout(advanced_box)
        self.rotate_combo = QComboBox(); self.rotate_combo.addItems(["0", "90", "180", "270"])
        self.content_rotate_combo = QComboBox(); self.content_rotate_combo.addItems(["0", "90", "180", "270"])
        self.roll_x_spin = QSpinBox(); self.roll_x_spin.setRange(-2000, 2000)
        self.roll_y_spin = QSpinBox(); self.roll_y_spin.setRange(-2000, 2000)
        self.reva_chunk_spin = QSpinBox(); self.reva_chunk_spin.setRange(1, 64); self.reva_chunk_spin.setValue(4)
        self.interval_spin = QSpinBox(); self.interval_spin.setRange(1, 60); self.interval_spin.setValue(1)
        self.raw_prefix_spin = QSpinBox(); self.raw_prefix_spin.setRange(0, 500000)
        self.raw_tail_spin = QSpinBox(); self.raw_tail_spin.setRange(0, 500000)
        self.x_byte_spin = QSpinBox(); self.x_byte_spin.setRange(0, 255)
        self.clear_cb = QCheckBox("clear before send")
        self.reset_cb = QCheckBox("legacy reset before frame")
        self.reva_no_orientation_cb = QCheckBox("RevA: no orientation cmd")
        adv.addWidget(QLabel("Rotate final"), 0, 0); adv.addWidget(self.rotate_combo, 0, 1)
        adv.addWidget(QLabel("Rotate content"), 1, 0); adv.addWidget(self.content_rotate_combo, 1, 1)
        adv.addWidget(QLabel("Roll X/Y"), 2, 0); adv.addWidget(self.roll_x_spin, 2, 1); adv.addWidget(self.roll_y_spin, 2, 2)
        adv.addWidget(QLabel("RevA chunk lines"), 3, 0); adv.addWidget(self.reva_chunk_spin, 3, 1)
        adv.addWidget(QLabel("Dashboard interval"), 4, 0); adv.addWidget(self.interval_spin, 4, 1)
        adv.addWidget(QLabel("Legacy prefix/tail"), 5, 0); adv.addWidget(self.raw_prefix_spin, 5, 1); adv.addWidget(self.raw_tail_spin, 5, 2)
        adv.addWidget(QLabel("X byte"), 6, 0); adv.addWidget(self.x_byte_spin, 6, 1)
        adv.addWidget(self.clear_cb, 7, 0); adv.addWidget(self.reset_cb, 7, 1); adv.addWidget(self.reva_no_orientation_cb, 7, 2)
        left.addWidget(advanced_box)

        actions = QGroupBox("Actions")
        action_grid = QGridLayout(actions)
        self.preview_btn = QPushButton("Preview"); self.preview_btn.clicked.connect(self.update_preview_auto)
        self.test_btn = QPushButton("Send test pattern"); self.test_btn.clicked.connect(self.send_test)
        self.send_btn = QPushButton("Send image once"); self.send_btn.clicked.connect(self.send_image_once)
        self.gif_btn = QPushButton("Play GIF"); self.gif_btn.clicked.connect(self.play_gif)
        self.dashboard_btn = QPushButton("Start dashboard"); self.dashboard_btn.clicked.connect(self.start_dashboard)
        self.stop_btn = QPushButton("Stop"); self.stop_btn.clicked.connect(self.stop_worker)
        self.save_btn = QPushButton("Save prepared PNG"); self.save_btn.clicked.connect(self.save_prepared)
        action_grid.addWidget(self.preview_btn, 0, 0); action_grid.addWidget(self.test_btn, 0, 1)
        action_grid.addWidget(self.send_btn, 1, 0); action_grid.addWidget(self.gif_btn, 1, 1)
        action_grid.addWidget(self.dashboard_btn, 2, 0); action_grid.addWidget(self.stop_btn, 2, 1)
        action_grid.addWidget(self.save_btn, 3, 0, 1, 2)
        left.addWidget(actions)

        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(110)
        left.addWidget(self.log)

        for widget in [self.width_spin, self.height_spin, self.safe_margin_spin, self.black_threshold_spin, self.gif_fps_spin, self.gif_max_spin]:
            widget.valueChanged.connect(self.schedule_preview)
        for widget in [self.fit_combo, self.rotate_combo, self.content_rotate_combo]:
            widget.currentIndexChanged.connect(self.schedule_preview)
        for widget in [self.green_cb, self.red_cb, self.black_cb]:
            widget.stateChanged.connect(self.schedule_preview)
        self.bg_edit.textChanged.connect(self.schedule_preview)
        self._preview_timer = QTimer(self); self._preview_timer.setSingleShot(True); self._preview_timer.timeout.connect(self.update_preview_auto)

    def schedule_preview(self) -> None:
        self._preview_timer.start(250)

    def settings_dict(self) -> dict:
        try:
            bg = hex_to_rgb(self.bg_edit.text())
        except Exception:
            bg = (0, 0, 0)
        return {
            "port": self.port_combo.currentText().strip() or "/dev/ttyACM0",
            "baud": int(self.baud_spin.value()),
            "protocol": self.protocol_combo.currentText(),
            "width": int(self.width_spin.value()),
            "height": int(self.height_spin.value()),
            "pixel_format": self.pixel_combo.currentText(),
            "brightness": int(self.brightness_slider.value()),
            "fit": self.fit_combo.currentText(),
            "bg": bg,
            "green_to_bg": self.green_cb.isChecked(),
            "red_to_blue": self.red_cb.isChecked(),
            "force_black": self.black_cb.isChecked(),
            "black_threshold": int(self.black_threshold_spin.value()),
            "safe_margin": int(self.safe_margin_spin.value()),
            "rotate": int(self.rotate_combo.currentText()),
            "content_rotate": int(self.content_rotate_combo.currentText()),
            "roll_x": int(self.roll_x_spin.value()),
            "roll_y": int(self.roll_y_spin.value()),
            "reva_chunk_lines": int(self.reva_chunk_spin.value()),
            "reva_no_orientation": self.reva_no_orientation_cb.isChecked(),
            "interval": int(self.interval_spin.value()),
            "raw_prefix_pixels": int(self.raw_prefix_spin.value()),
            "raw_tail_pixels": int(self.raw_tail_spin.value()),
            "x_byte": int(self.x_byte_spin.value()),
            "clear": self.clear_cb.isChecked(),
            "reset_before_frame": self.reset_cb.isChecked(),
            "title": self.title_edit.text().strip() or "TURMO Linux",
            "gif_fps": float(self.gif_fps_spin.value()),
            "gif_loop": self.gif_loop_cb.isChecked(),
            "gif_max_frames": int(self.gif_max_spin.value()),
        }

    def save_settings(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = self.settings_dict()
            data["image_path"] = self.image_path
            data["gif_path"] = self.gif_path
            data["bg_hex"] = self.bg_edit.text()
            CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            self.add_log(f"Settings save failed: {exc}")

    def load_settings(self) -> None:
        if not CONFIG_PATH.exists():
            return
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            self.protocol_combo.setCurrentText(data.get("protocol", "reva"))
            self.baud_spin.setValue(int(data.get("baud", 4000000)))
            self.width_spin.setValue(int(data.get("width", 320)))
            self.height_spin.setValue(int(data.get("height", 480)))
            self.pixel_combo.setCurrentText(data.get("pixel_format", "rgb565le"))
            self.fit_combo.setCurrentText(data.get("fit", "contain"))
            self.bg_edit.setText(data.get("bg_hex", rgb_to_hex(tuple(data.get("bg", (0, 0, 0))))))
            self.green_cb.setChecked(bool(data.get("green_to_bg", True)))
            self.red_cb.setChecked(bool(data.get("red_to_blue", True)))
            self.black_cb.setChecked(bool(data.get("force_black", True)))
            self.safe_margin_spin.setValue(int(data.get("safe_margin", 0)))
            self.black_threshold_spin.setValue(int(data.get("black_threshold", 45)))
            self.rotate_combo.setCurrentText(str(data.get("rotate", 0)))
            self.content_rotate_combo.setCurrentText(str(data.get("content_rotate", 0)))
            self.roll_x_spin.setValue(int(data.get("roll_x", 0)))
            self.roll_y_spin.setValue(int(data.get("roll_y", 0)))
            self.reva_chunk_spin.setValue(int(data.get("reva_chunk_lines", 4)))
            self.reva_no_orientation_cb.setChecked(bool(data.get("reva_no_orientation", False)))
            self.interval_spin.setValue(int(data.get("interval", 1)))
            self.raw_prefix_spin.setValue(int(data.get("raw_prefix_pixels", 0)))
            self.raw_tail_spin.setValue(int(data.get("raw_tail_pixels", 0)))
            self.x_byte_spin.setValue(int(data.get("x_byte", 0)))
            self.clear_cb.setChecked(bool(data.get("clear", False)))
            self.reset_cb.setChecked(bool(data.get("reset_before_frame", False)))
            self.title_edit.setText(data.get("title", "TURMO Linux"))
            self.gif_fps_spin.setValue(float(data.get("gif_fps", 8.0)))
            self.gif_loop_cb.setChecked(bool(data.get("gif_loop", True)))
            self.gif_max_spin.setValue(int(data.get("gif_max_frames", 300)))
            self.image_path = data.get("image_path") if data.get("image_path") and Path(data.get("image_path")).exists() else None
            self.gif_path = data.get("gif_path") if data.get("gif_path") and Path(data.get("gif_path")).exists() else None
            if self.image_path:
                self.image_label.setText(self.image_path)
            elif self.gif_path:
                self.image_label.setText(self.gif_path)
        except Exception as exc:
            self.add_log(f"Settings load failed: {exc}")

    def add_log(self, text: str) -> None:
        self.log.append(text)

    def refresh_ports(self) -> None:
        old = self.port_combo.currentText().strip()
        self.port_combo.clear()
        ports = core.find_candidate_ports()
        if not ports:
            self.port_combo.addItem(old or "/dev/ttyACM0")
            self.add_log("No serial ports found. Try USB cable/port or check usbview.")
            return
        for port, label in ports:
            self.port_combo.addItem(port, label)
        if old:
            idx = self.port_combo.findText(old)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        self.add_log("Ports refreshed: " + ", ".join(p for p, _ in ports))

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open image", str(Path.home()), "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All files (*)")
        if not path:
            return
        self.image_path = path
        self.gif_path = None
        self.image_label.setText(path)
        self.update_preview_image(path)
        self.save_settings()

    def open_gif(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open GIF", str(Path.home()), "GIF files (*.gif);;Images (*.gif *.png *.jpg *.jpeg *.webp *.bmp);;All files (*)")
        if not path:
            return
        self.gif_path = path
        self.image_path = None
        self.image_label.setText(path)
        self.update_preview_gif(path)
        self.save_settings()

    def _make_preview_args(self, mode: str, image_path: Optional[str] = None) -> SimpleNamespace:
        s = self.settings_dict()
        return SimpleNamespace(
            image=image_path if mode == "image" else None,
            test_pattern=mode == "test",
            width=s["width"], height=s["height"], fit=s["fit"], bg=s["bg"],
            green_to_bg=s["green_to_bg"], red_to_blue=s["red_to_blue"], force_black=s["force_black"],
            black_threshold=s["black_threshold"], safe_margin=s["safe_margin"],
            rotate=s["rotate"], content_rotate=s["content_rotate"], roll_x=s["roll_x"], roll_y=s["roll_y"],
            title=s["title"],
        )

    def update_preview_auto(self) -> None:
        if self.gif_path:
            self.update_preview_gif(self.gif_path)
        elif self.image_path:
            self.update_preview_image(self.image_path)
        else:
            self.update_preview_dashboard()

    def update_preview_image(self, path: Optional[str] = None) -> None:
        path = path or self.image_path
        if not path:
            self.add_log("Open an image first.")
            return
        try:
            img = core.make_frame(self._make_preview_args("image", path))
            self.preview.set_pil(img)
            self.add_log(f"Preview image: {img.size[0]}x{img.size[1]}")
        except Exception as exc:
            self.add_log(f"Preview failed: {exc}")

    def update_preview_gif(self, path: Optional[str] = None) -> None:
        path = path or self.gif_path
        if not path:
            self.add_log("Open a GIF first.")
            return
        try:
            s = self.settings_dict()
            frames = core.prepare_gif_frames(
                path, width=s["width"], height=s["height"], fit=s["fit"], bg=s["bg"],
                green_to_bg=s["green_to_bg"], red_to_blue=s["red_to_blue"], force_black=s["force_black"],
                black_threshold=s["black_threshold"], safe_margin=s["safe_margin"],
                rotate=s["rotate"], content_rotate=s["content_rotate"], fps_limit=s["gif_fps"], max_frames=1,
            )
            self.preview.set_pil(frames[0][0])
            self.add_log(f"Preview GIF first frame: {frames[0][0].size[0]}x{frames[0][0].size[1]}")
        except Exception as exc:
            self.add_log(f"GIF preview failed: {exc}")

    def update_preview_dashboard(self) -> None:
        try:
            img = core.make_frame(self._make_preview_args("dashboard"))
            self.preview.set_pil(img)
        except Exception as exc:
            self.add_log(f"Dashboard preview failed: {exc}")

    def save_prepared(self) -> None:
        path = self.image_path or self.gif_path
        if not path:
            QMessageBox.information(self, APP_NAME, "Open an image or GIF first.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Save prepared PNG", "prepared_320x480.png", "PNG (*.png)")
        if not out:
            return
        try:
            if self.gif_path:
                s = self.settings_dict()
                img = core.prepare_gif_frames(self.gif_path, width=s["width"], height=s["height"], fit=s["fit"], bg=s["bg"], green_to_bg=s["green_to_bg"], red_to_blue=s["red_to_blue"], force_black=s["force_black"], black_threshold=s["black_threshold"], safe_margin=s["safe_margin"], rotate=s["rotate"], content_rotate=s["content_rotate"], fps_limit=s["gif_fps"], max_frames=1)[0][0]
            else:
                img = core.make_frame(self._make_preview_args("image", self.image_path))
            img.save(out)
            self.add_log(f"Saved prepared image: {out}")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def _start_worker(self, mode: str, path: Optional[str] = None) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, APP_NAME, "Worker is already running. Press Stop first.")
            return
        self.save_settings()
        self.worker = SendWorker(self.settings_dict(), mode, image_path=path)
        self.worker.status.connect(self.add_log)
        self.worker.failed.connect(self.worker_failed)
        self.worker.finished_ok.connect(self.worker_finished)
        self.worker.start()

    def send_test(self) -> None:
        self._start_worker("test")

    def send_image_once(self) -> None:
        if not self.image_path:
            QMessageBox.information(self, APP_NAME, "Open an image first.")
            return
        self._start_worker("image", self.image_path)

    def play_gif(self) -> None:
        if not self.gif_path:
            QMessageBox.information(self, APP_NAME, "Open a GIF first.")
            return
        self._start_worker("gif", self.gif_path)

    def start_dashboard(self) -> None:
        self._start_worker("dashboard")

    def stop_worker(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("Stopping...")
        else:
            self.add_log("Nothing running.")

    def worker_failed(self, text: str) -> None:
        self.add_log("ERROR: " + text.replace("\n", " | "))
        QMessageBox.critical(self, APP_NAME, text)

    def worker_finished(self, text: str) -> None:
        self.add_log(text)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.save_settings()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1500)
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
