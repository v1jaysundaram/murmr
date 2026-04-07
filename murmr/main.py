import logging
import math
import os
import threading
import time
import tkinter as tk

import pyperclip
import pystray
from PIL import Image, ImageDraw, ImageFont
from pynput import keyboard as kb
from pynput.keyboard import Controller as KeyboardController, Key

from config import WHISPER_MODEL
from notion_writer import append_to_notion
from recorder import get_rms, start_recording, stop_recording
from transcriber import Transcriber

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_log_path = os.path.join(os.path.dirname(__file__), "murmr.log")
logging.basicConfig(
    filename=_log_path,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_is_recording = False
_transcriber = None
_keyboard = KeyboardController()

# Hotkey: hold Ctrl, press Win to toggle
_pressed_keys = set()
_combo_fired = False
_CTRL_KEYS = {kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r}

# Notion toggle
_notion_enabled = False

# Tray
_tray_icon = None

# Overlay
_tk_root = None
_overlay = None
_bar_canvas = None
_bar_rects = []
_bar_phase = 0.0
_animate_job = None

# Overlay design constants
OVERLAY_W  = 140
OVERLAY_H  = 40
NUM_BARS   = 7
BAR_W      = 2
BAR_GAP    = 5
BAR_ON     = "#ffffff"   # white — recording
BAR_OFF    = "#2a2a2a"   # almost invisible — transcribing
CHROMA_KEY = "#ff00ff"   # transparent hole colour (never used in the design)


# ---------------------------------------------------------------------------
# Tray icon (PIL-drawn "M" lettermark)
# ---------------------------------------------------------------------------

def _make_tray_icon(recording=False):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = (200, 50, 50) if recording else (45, 45, 48)
    draw.rounded_rectangle([2, 2, size - 2, size - 2], radius=12, fill=bg)
    try:
        font = ImageFont.truetype("arialbd.ttf", 36)
    except (IOError, OSError):
        font = ImageFont.load_default()
    draw.text((size // 2, size // 2), "M", fill=(255, 255, 255), anchor="mm", font=font)
    return img


# ---------------------------------------------------------------------------
# Overlay — pill with true transparent corners + reactive bars
# ---------------------------------------------------------------------------

def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Smooth rounded rectangle via polygon (standard tkinter trick)."""
    pts = [
        x1+r, y1,   x2-r, y1,
        x2,   y1,   x2,   y1+r,
        x2,   y2-r, x2,   y2,
        x2-r, y2,   x1+r, y2,
        x1,   y2,   x1,   y2-r,
        x1,   y1+r, x1,   y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


def _build_overlay():
    global _overlay, _bar_canvas, _bar_rects

    _overlay = tk.Toplevel(_tk_root)
    _overlay.overrideredirect(True)
    _overlay.attributes("-topmost", True)
    _overlay.attributes("-alpha", 0.88)
    _overlay.configure(bg=CHROMA_KEY)
    _overlay.wm_attributes("-transparentcolor", CHROMA_KEY)  # real transparent corners

    sw = _overlay.winfo_screenwidth()
    sh = _overlay.winfo_screenheight()
    x = (sw - OVERLAY_W) // 2
    y = sh - OVERLAY_H - 72
    _overlay.geometry(f"{OVERLAY_W}x{OVERLAY_H}+{x}+{y}")

    _bar_canvas = tk.Canvas(
        _overlay, width=OVERLAY_W, height=OVERLAY_H,
        bg=CHROMA_KEY, highlightthickness=0,
    )
    _bar_canvas.pack()

    r = OVERLAY_H // 2  # full pill radius

    # Outer subtle border ring
    _rounded_rect(_bar_canvas, 0, 0, OVERLAY_W, OVERLAY_H, r,
                  fill="#1a1a1a", outline="")
    # Inner black pill — 1px inset
    _rounded_rect(_bar_canvas, 1, 1, OVERLAY_W-1, OVERLAY_H-1, r-1,
                  fill="#080808", outline="")

    # Bars — centred
    total_bar_w = NUM_BARS * BAR_W + (NUM_BARS - 1) * BAR_GAP
    start_x = (OVERLAY_W - total_bar_w) // 2
    cy = OVERLAY_H // 2

    _bar_rects.clear()
    for i in range(NUM_BARS):
        x0 = start_x + i * (BAR_W + BAR_GAP)
        rect = _bar_canvas.create_rectangle(
            x0, cy - 3, x0 + BAR_W, cy + 3,
            fill=BAR_ON, outline="",
        )
        _bar_rects.append((rect, x0))


def _show_overlay():
    global _bar_phase
    _bar_phase = 0.0
    _build_overlay()
    _animate_bars()


def _hide_overlay():
    global _overlay, _bar_canvas, _bar_rects, _animate_job
    if _animate_job:
        try:
            _bar_canvas.after_cancel(_animate_job)
        except Exception:
            pass
        _animate_job = None
    if _overlay:
        _overlay.destroy()
        _overlay = None
    _bar_canvas = None
    _bar_rects = []


def _animate_bars():
    """
    Reactive animation: bar heights are driven by live mic RMS level,
    modulated by a sine wave per bar so they move independently.
    """
    global _bar_phase, _animate_job

    if not _bar_canvas or not _overlay:
        return

    cy    = OVERLAY_H // 2
    level = get_rms()           # 0.0 – 1.0 from recorder
    min_h = 2.0
    max_h = (OVERLAY_H // 2) - 4   # max usable half-height

    for i, (rect, x0) in enumerate(_bar_rects):
        # Sine modulation per bar, scaled by actual mic level
        wave   = 0.5 + 0.5 * math.sin(_bar_phase + i * 0.9)
        height = min_h + (max_h - min_h) * wave * max(level, 0.08)
        _bar_canvas.coords(rect, x0, cy - height, x0 + BAR_W, cy + height)

    _bar_phase += 0.22
    _animate_job = _bar_canvas.after(35, _animate_bars)


# ---------------------------------------------------------------------------
# Thread-safe UI helper
# ---------------------------------------------------------------------------

def _ui(fn):
    if _tk_root:
        _tk_root.after(0, fn)


# ---------------------------------------------------------------------------
# Paste helper
# ---------------------------------------------------------------------------

def do_paste(text):
    pyperclip.copy(text)
    time.sleep(0.15)  # let the target window regain focus after the hotkey is released
    _keyboard.press(Key.ctrl)
    _keyboard.press('v')
    _keyboard.release('v')
    _keyboard.release(Key.ctrl)


# ---------------------------------------------------------------------------
# Recording → transcription → paste flow
# ---------------------------------------------------------------------------

def _transcription_worker():
    global _is_recording

    audio = stop_recording()
    logging.info("Transcribing...")

    def _dim_bars():
        if _bar_canvas:
            for rect, _ in _bar_rects:
                _bar_canvas.itemconfig(rect, fill=BAR_OFF)

    _ui(_dim_bars)

    text = _transcriber.transcribe(audio).strip()

    if text:
        logging.info("Transcribed: %s", text)
        do_paste(text)
        if _notion_enabled:
            def _notion_worker():
                try:
                    append_to_notion(text)
                except Exception as e:
                    logging.error("Notion write failed: %s", e)
                    if _tray_icon:
                        _tray_icon.notify("Notion write failed — check murmr.log", "murmr")
            threading.Thread(target=_notion_worker, daemon=True).start()
    else:
        logging.warning("Nothing transcribed — try speaking louder.")

    _is_recording = False
    _ui(_hide_overlay)
    if _tray_icon:
        _tray_icon.icon = _make_tray_icon(recording=False)


# ---------------------------------------------------------------------------
# Toggle recording
# ---------------------------------------------------------------------------

def _toggle_recording():
    global _is_recording

    if _transcriber is None:
        logging.warning("Hotkey pressed but model is still loading — ignoring.")
        return

    if not _is_recording:
        _is_recording = True
        if _tray_icon:
            _tray_icon.icon = _make_tray_icon(recording=True)
        _ui(_show_overlay)
        start_recording()
        logging.info("Recording started.")
    else:
        logging.info("Recording stopped.")
        threading.Thread(target=_transcription_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Keyboard listener — Ctrl+Win to toggle
# ---------------------------------------------------------------------------

def on_key_press(key):
    global _combo_fired
    _pressed_keys.add(key)
    if key == kb.Key.cmd and (_pressed_keys & _CTRL_KEYS) and not _combo_fired:
        _combo_fired = True
        _toggle_recording()


def on_key_release(key):
    global _combo_fired
    _pressed_keys.discard(key)
    if key == kb.Key.cmd:
        _combo_fired = False


# ---------------------------------------------------------------------------
# Tray menu
# ---------------------------------------------------------------------------

def _toggle_notion(icon, item):
    global _notion_enabled
    _notion_enabled = not _notion_enabled
    logging.info("Notion logging %s.", "enabled" if _notion_enabled else "disabled")


def _quit(icon, item):
    icon.stop()
    _ui(_tk_root.destroy)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global _transcriber, _tray_icon, _tk_root

    _tk_root = tk.Tk()
    _tk_root.withdraw()

    def _load_model():
        global _transcriber
        logging.info("Loading Whisper model...")
        _transcriber = Transcriber()
        logging.info("Ready. Press Ctrl+Win to start/stop dictation.")

    threading.Thread(target=_load_model, daemon=True).start()

    listener = kb.Listener(on_press=on_key_press, on_release=on_key_release)
    listener.daemon = True
    listener.start()

    menu = pystray.Menu(
        pystray.MenuItem("murmr", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Log to Notion",
            _toggle_notion,
            checked=lambda item: _notion_enabled,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _quit),
    )
    _tray_icon = pystray.Icon("murmr", _make_tray_icon(), "murmr — Ctrl+Win to record", menu)
    _tray_icon.run_detached()

    _tk_root.mainloop()
    logging.info("murmr exited.")


if __name__ == "__main__":
    main()
