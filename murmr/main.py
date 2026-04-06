import threading
import time

import pyperclip
import pystray
from PIL import Image, ImageDraw
from pynput import keyboard as kb
from pynput.keyboard import Controller as KeyboardController, Key

from config import HOTKEY_COMBO, WHISPER_MODEL
from recorder import start_recording, stop_recording
from transcriber import Transcriber

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_is_recording = False
_transcriber = None
_tray_icon = None
_keyboard = KeyboardController()
_pressed_keys = set()


# ---------------------------------------------------------------------------
# Tray icon drawing
# ---------------------------------------------------------------------------

def make_icon(recording=False):
    """Draw a simple circular tray icon. Red when recording, grey when idle."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if recording:
        # Outer red circle
        draw.ellipse([4, 4, size - 4, size - 4], fill=(210, 50, 50))
        # White dot in centre — the "recording" indicator
        draw.ellipse([24, 24, 40, 40], fill=(255, 255, 255))
    else:
        # Solid dark grey circle — idle
        draw.ellipse([4, 4, size - 4, size - 4], fill=(70, 70, 70))

    return img


# ---------------------------------------------------------------------------
# Paste helper
# ---------------------------------------------------------------------------

def do_paste(text):
    """Copy text to clipboard then simulate Ctrl+V to paste at cursor."""
    pyperclip.copy(text)
    time.sleep(0.15)  # Give clipboard time to update before sending the shortcut
    _keyboard.press(Key.ctrl)
    _keyboard.press('v')
    _keyboard.release('v')
    _keyboard.release(Key.ctrl)


# ---------------------------------------------------------------------------
# Recording → transcription → paste flow
# ---------------------------------------------------------------------------

def _transcription_worker():
    """
    Runs in a background thread so the tray doesn't freeze during transcription.
    Sequence: stop mic → transcribe → paste → reset icon.
    """
    global _is_recording

    audio = stop_recording()
    print("[murmr] Transcribing...")

    text = _transcriber.transcribe(audio).strip()

    if text:
        print(f"[murmr] '{text}'")
        do_paste(text)
    else:
        print("[murmr] Nothing transcribed — try speaking louder.")

    _is_recording = False
    if _tray_icon:
        _tray_icon.icon = make_icon(recording=False)


# ---------------------------------------------------------------------------
# Hotkey parsing
# ---------------------------------------------------------------------------

def _parse_hotkey(combo_str):
    """
    Turn 'ctrl+shift+space' into a list of modifier names and a trigger key.
    Returns: (modifiers: list[str], trigger: Key or str)
    """
    parts = combo_str.lower().split("+")
    modifiers = []
    trigger = None
    special = {"space": Key.space, "enter": Key.enter, "tab": Key.tab}

    for part in parts:
        if part in ("ctrl", "shift", "alt"):
            modifiers.append(part)
        elif part in special:
            trigger = special[part]
        else:
            trigger = part  # single character like 'm'

    return modifiers, trigger


_required_modifiers, _trigger_key = _parse_hotkey(HOTKEY_COMBO)


def _modifiers_held():
    """Return True if all required modifier keys are currently pressed."""
    for mod in _required_modifiers:
        if mod == "ctrl" and not (_pressed_keys & {kb.Key.ctrl_l, kb.Key.ctrl_r, kb.Key.ctrl}):
            return False
        if mod == "shift" and not (_pressed_keys & {kb.Key.shift, kb.Key.shift_l, kb.Key.shift_r}):
            return False
        if mod == "alt" and not (_pressed_keys & {kb.Key.alt_l, kb.Key.alt_r, kb.Key.alt}):
            return False
    return True


# ---------------------------------------------------------------------------
# Keyboard listener callbacks
# ---------------------------------------------------------------------------

def on_key_press(key):
    global _is_recording
    _pressed_keys.add(key)

    if key == _trigger_key and _modifiers_held() and not _is_recording:
        _is_recording = True
        if _tray_icon:
            _tray_icon.icon = make_icon(recording=True)
        start_recording()
        print("[murmr] Recording...")


def on_key_release(key):
    if key == _trigger_key and _is_recording:
        print("[murmr] Stopped.")
        threading.Thread(target=_transcription_worker, daemon=True).start()

    _pressed_keys.discard(key)


# ---------------------------------------------------------------------------
# Tray menu
# ---------------------------------------------------------------------------

def _quit(icon, item):
    icon.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global _transcriber, _tray_icon

    print("[murmr] Loading Whisper model — this takes a few seconds on first run...")
    _transcriber = Transcriber()
    print(f"[murmr] Ready. Hold {HOTKEY_COMBO} to dictate.")

    # Keyboard listener runs in its own background thread
    listener = kb.Listener(on_press=on_key_press, on_release=on_key_release)
    listener.daemon = True
    listener.start()

    # Tray icon must run on the main thread (Windows requirement)
    menu = pystray.Menu(
        pystray.MenuItem("murmr", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _quit),
    )
    _tray_icon = pystray.Icon("murmr", make_icon(), "murmr", menu)
    _tray_icon.run()  # Blocks here until Quit is clicked


if __name__ == "__main__":
    main()
