import logging
import math
import os
import threading
import time
import tkinter as tk

import pyperclip
import pystray
from PIL import Image, ImageDraw, ImageFont
from pynput.keyboard import Controller as KeyboardController, Key

import hotkeys
from config import DOCK_X, DOCK_Y, OVERLAY_THEME, WHISPER_MODEL
from dock import Dock
from notion_writer import append_to_notion
from recorder import get_rms, start_recording, stop_recording
from settings_window import open_settings
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
_is_recording  = False
_transcriber   = None
_keyboard      = KeyboardController()

# Notion toggle
_notion_enabled = False

# Tray
_tray_icon = None

# Dock
_dock = None

# Overlay
_tk_root    = None
_overlay    = None
_bar_canvas = None
_bar_rects  = []
_bar_phase  = 0.0
_animate_job = None

# Current theme (updated by settings)
_overlay_theme = OVERLAY_THEME

# .env path
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------
THEMES = {
    "dark": {
        "outer":  "#1a1a1a",
        "inner":  "#080808",
        "bar_on": "#ffffff",
        "bar_off": "#2a2a2a",
    },
    "light": {
        "outer":  "#cccccc",
        "inner":  "#f0f0f0",
        "bar_on": "#222222",
        "bar_off": "#cccccc",
    },
}

# Overlay design constants
OVERLAY_W  = 140
OVERLAY_H  = 40
NUM_BARS   = 7
BAR_W      = 2
BAR_GAP    = 5
CHROMA_KEY = "#ff00ff"   # transparent hole colour (never used in the design)


# ---------------------------------------------------------------------------
# Tray icon (PIL-drawn "M" lettermark)
# ---------------------------------------------------------------------------

def _make_tray_icon(recording=False):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = (76, 175, 80) if recording else (45, 45, 48)  # green while recording
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

    logging.info("Building overlay — theme: %s", _overlay_theme)
    theme = THEMES.get(_overlay_theme, THEMES["dark"])

    _overlay = tk.Toplevel(_tk_root)
    _overlay.overrideredirect(True)
    _overlay.attributes("-topmost", True)
    _overlay.attributes("-alpha", 0.88)
    _overlay.configure(bg=CHROMA_KEY)
    _overlay.wm_attributes("-transparentcolor", CHROMA_KEY)

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

    r = OVERLAY_H // 2

    _rounded_rect(_bar_canvas, 0, 0, OVERLAY_W, OVERLAY_H, r,
                  fill=theme["outer"], outline="")
    _rounded_rect(_bar_canvas, 1, 1, OVERLAY_W-1, OVERLAY_H-1, r-1,
                  fill=theme["inner"], outline="")

    total_bar_w = NUM_BARS * BAR_W + (NUM_BARS - 1) * BAR_GAP
    start_x = (OVERLAY_W - total_bar_w) // 2
    cy = OVERLAY_H // 2

    _bar_rects.clear()
    for i in range(NUM_BARS):
        x0 = start_x + i * (BAR_W + BAR_GAP)
        rect = _bar_canvas.create_rectangle(
            x0, cy - 3, x0 + BAR_W, cy + 3,
            fill=theme["bar_on"], outline="",
        )
        _bar_rects.append((rect, x0, theme["bar_on"], theme["bar_off"]))


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
    global _bar_phase, _animate_job

    if not _bar_canvas or not _overlay:
        return

    cy    = OVERLAY_H // 2
    level = get_rms()
    min_h = 2.0
    max_h = (OVERLAY_H // 2) - 4

    for i, (rect, x0, bar_on, _bar_off) in enumerate(_bar_rects):
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
    time.sleep(0.15)
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

    _ui(lambda: _dock.update_status("transcribing") if _dock else None)

    def _dim_bars():
        if _bar_canvas:
            for rect, _, _bar_on, bar_off in _bar_rects:
                _bar_canvas.itemconfig(rect, fill=bar_off)

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
    _ui(lambda: _dock.update_status("idle") if _dock else None)
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
        _ui(lambda: _dock.update_status("recording") if _dock else None)
        start_recording()
        logging.info("Recording started.")
    else:
        logging.info("Recording stopped.")
        threading.Thread(target=_transcription_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Push-to-talk handlers
# ---------------------------------------------------------------------------

def _ptt_start():
    global _is_recording

    if _transcriber is None:
        logging.warning("PTT pressed but model is still loading — ignoring.")
        return

    if _is_recording:
        return  # Don't interrupt an active toggle-mode session

    _is_recording = True
    if _tray_icon:
        _tray_icon.icon = _make_tray_icon(recording=True)
    _ui(_show_overlay)
    _ui(lambda: _dock.update_status("recording") if _dock else None)
    start_recording()
    logging.info("PTT recording started.")


def _ptt_stop():
    if not _is_recording:
        return
    logging.info("PTT recording stopped.")
    threading.Thread(target=_transcription_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Notion toggle (shared setter used by dock, tray, and settings)
# ---------------------------------------------------------------------------

def _set_notion_enabled(value: bool):
    global _notion_enabled
    _notion_enabled = value
    logging.info("Notion logging %s.", "enabled" if value else "disabled")
    if _dock:
        _ui(lambda: _dock.update_notion_button(value))
    if _tray_icon:
        _tray_icon.update_menu()   # keep tray checkbox in sync


def _toggle_notion_from_tray(icon, item):
    _set_notion_enabled(not _notion_enabled)


# ---------------------------------------------------------------------------
# Theme change callback (from settings)
# ---------------------------------------------------------------------------

def _on_theme_change(theme: str):
    global _overlay_theme
    _overlay_theme = theme
    logging.info("Theme callback fired — overlay_theme is now: %s", theme)


# ---------------------------------------------------------------------------
# Settings opener
# ---------------------------------------------------------------------------

def _open_settings():
    open_settings(
        tk_root=_tk_root,
        get_notion_enabled=lambda: _notion_enabled,
        set_notion_enabled=_set_notion_enabled,
        on_theme_change=_on_theme_change,
        env_path=_ENV_PATH,
    )


# ---------------------------------------------------------------------------
# Tray menu
# ---------------------------------------------------------------------------

def _quit(icon, item):
    icon.stop()
    _ui(_tk_root.destroy)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global _transcriber, _tray_icon, _tk_root, _dock

    _tk_root = tk.Tk()
    _tk_root.withdraw()

    def _load_model():
        global _transcriber
        logging.info("Loading Whisper model...")
        _transcriber = Transcriber()
        logging.info("Ready. Ctrl+Win to toggle hands-free  |  Hold Ctrl+Alt+Win for push-to-talk.")

    threading.Thread(target=_load_model, daemon=True).start()

    # Parse saved dock position
    try:
        dock_x = int(DOCK_X) if DOCK_X else None
        dock_y = int(DOCK_Y) if DOCK_Y else None
    except ValueError:
        dock_x = dock_y = None

    _dock = Dock(
        tk_root=_tk_root,
        on_notion_toggle=lambda: _set_notion_enabled(not _notion_enabled),
        on_open_settings=_open_settings,
        env_path=_ENV_PATH,
        initial_x=dock_x,
        initial_y=dock_y,
    )

    hotkeys.start_listener(
        on_toggle=_toggle_recording,
        on_ptt_start=_ptt_start,
        on_ptt_stop=_ptt_stop,
        is_recording=lambda: _is_recording,
    )

    menu = pystray.Menu(
        pystray.MenuItem("murmr", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Notion logging",
            _toggle_notion_from_tray,
            checked=lambda item: _notion_enabled,
        ),
        pystray.MenuItem(
            "AI cleanup",
            None,
            checked=lambda item: False,
            enabled=False,
        ),
        pystray.MenuItem("Settings", lambda icon, item: _ui(_open_settings)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _quit),
    )
    _tray_icon = pystray.Icon(
        "murmr", _make_tray_icon(),
        "murmr  |  Ctrl+Win → toggle hands-free  |  Hold Ctrl+Alt+Win → push-to-talk",
        menu,
    )
    _tray_icon.run_detached()

    _tk_root.mainloop()
    logging.info("murmr exited.")


if __name__ == "__main__":
    main()
