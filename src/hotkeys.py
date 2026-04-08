"""
hotkeys.py — global keyboard listener for murmr.

Two recording modes:
  - Toggle / hands-free (Ctrl+Win):   tap Win while Ctrl is down → starts
                                       recording. Same combo again → stops.
  - Push-to-talk (Ctrl+Win+Alt hold): hold Win while Ctrl+Alt are down →
                                       records. Release Win → transcribes.

Timing safety net:
  When Ctrl+Win fires, we wait 60 ms before committing to toggle mode.
  If Alt arrives within that window the action is promoted to PTT instead.
  This handles the case where the user presses Ctrl+Win+Alt "together" but
  Alt registers a few milliseconds after Win.
"""

import threading

from pynput import keyboard as kb

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
_pressed_keys  = set()
_combo_fired   = False
_ptt_active    = False
_pending_timer = None   # debounce timer — waits to see if Alt arrives

_CTRL_KEYS = {kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r}
_ALT_KEYS  = {kb.Key.alt,  kb.Key.alt_l,  kb.Key.alt_r}

# Callbacks — set by start_listener()
_on_toggle    = None
_on_ptt_start = None
_on_ptt_stop  = None

_DEBOUNCE_S = 0.06   # 60 ms window to detect a late-arriving Alt key


def start_listener(on_toggle, on_ptt_start, on_ptt_stop, is_recording):
    """
    Start the global keyboard listener and return it.

    on_toggle:    callable() — toggle recording on/off (hands-free)
    on_ptt_start: callable() — begin push-to-talk recording
    on_ptt_stop:  callable() — end push-to-talk + transcribe
    is_recording: callable() → bool — kept for API compatibility
    """
    global _on_toggle, _on_ptt_start, _on_ptt_stop
    _on_toggle    = on_toggle
    _on_ptt_start = on_ptt_start
    _on_ptt_stop  = on_ptt_stop

    listener = kb.Listener(on_press=_on_key_press, on_release=_on_key_release)
    listener.daemon = True
    listener.start()
    return listener


# ---------------------------------------------------------------------------
# Key press
# ---------------------------------------------------------------------------

def _on_key_press(key):
    global _combo_fired, _ptt_active, _pending_timer
    _pressed_keys.add(key)

    if key != kb.Key.cmd:
        return

    if not (_pressed_keys & _CTRL_KEYS):
        return          # Ctrl not held — ignore

    if _combo_fired:
        return          # already acted on this press cycle

    _combo_fired = True

    if _pressed_keys & _ALT_KEYS:
        # Ctrl+Alt+Win — Alt was already held: PTT immediately, no debounce needed
        _cancel_pending()
        _ptt_active = True
        if _on_ptt_start:
            _on_ptt_start()
    else:
        # Ctrl+Win only so far — wait 60 ms to see if Alt arrives (PTT intent)
        _pending_timer = threading.Timer(_DEBOUNCE_S, _commit_toggle_or_ptt)
        _pending_timer.daemon = True
        _pending_timer.start()


def _commit_toggle_or_ptt():
    """Called 60 ms after Ctrl+Win. Decides toggle vs PTT based on whether Alt arrived."""
    global _ptt_active
    if not _combo_fired:
        return   # Win was already released before timer fired; nothing to do
    if _pressed_keys & _ALT_KEYS:
        # Alt arrived in the debounce window — treat as PTT
        _ptt_active = True
        if _on_ptt_start:
            _on_ptt_start()
    else:
        # No Alt — genuine toggle / hands-free
        if _on_toggle:
            _on_toggle()


def _cancel_pending():
    global _pending_timer
    if _pending_timer is not None:
        _pending_timer.cancel()
        _pending_timer = None


# ---------------------------------------------------------------------------
# Key release
# ---------------------------------------------------------------------------

def _on_key_release(key):
    global _combo_fired, _ptt_active
    _pressed_keys.discard(key)

    if key != kb.Key.cmd:
        return

    _cancel_pending()   # kill the debounce timer if still waiting

    if _ptt_active:
        # PTT was active — release Win → stop recording
        _ptt_active  = False
        _combo_fired = False
        if _on_ptt_stop:
            _on_ptt_stop()
    else:
        # Toggle mode or Win released before timer fired — just reset
        _combo_fired = False
