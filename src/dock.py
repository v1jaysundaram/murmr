"""
dock.py — Floating mini-dock for murmr.

A small always-on-top pill window with true rounded corners (chroma-key trick).
Draggable. Position persists to .env. Supports collapse/expand.

Full layout:   ● murmr  [AI] [N] [⚙] [–] [✕]
Collapsed:     ● [+]
"""

import tkinter as tk

from settings_window import _write_env

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
CHROMA        = "#fe00fe"   # transparent hole — must not appear in the design
DOCK_BG       = "#141414"
DOCK_FG       = "#d4d4d4"
DOCK_FG_DIM   = "#3a3a3a"
DOCK_BTN_HOVER = "#2a2a2a"

NOTION_ON_FG  = "#4fc3f7"
NOTION_OFF_FG = "#444444"
AI_ON_FG      = "#a5d6a7"   # soft green when AI cleanup is active
AI_OFF_FG     = "#444444"

STATUS_IDLE   = "#3a3a3a"
STATUS_REC    = "#4caf50"   # green for recording
STATUS_BUSY   = "#ff9800"   # amber for transcribing

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------
DOCK_H       = 34
DOCK_W_FULL  = 250
DOCK_W_MINI  = 58

DOT_R    = 4   # status dot radius
DOT_CX   = 16  # status dot center-x

LABEL_X  = 26
LABEL_W  = 68

# Button x positions in full mode (each 26px wide)
BTN_L_X   = LABEL_X + LABEL_W + 4   # 98
BTN_N_X   = BTN_L_X + 28            # 126
BTN_G_X   = BTN_N_X + 28            # 154
BTN_MIN_X = BTN_G_X + 28            # 182
BTN_X_X   = BTN_MIN_X + 28          # 210
# Total: 210 + 26 + 14 padding = 250 ✓

# Mini mode expand button
BTN_EXP_X = 26


def _pill_pts(w, h):
    """Return polygon points for a full-width pill of size w × h."""
    r = h // 2
    return [
        r,   0,    w-r, 0,
        w,   0,    w,   r,
        w,   h-r,  w,   h,
        w-r, h,    r,   h,
        0,   h,    0,   h-r,
        0,   r,    0,   0,
    ]


class Dock:
    def __init__(self, tk_root, on_notion_toggle, on_ai_toggle, on_open_settings,
                 env_path, initial_x=None, initial_y=None, initial_ai=False,
                 on_quit=None):
        self._root          = tk_root
        self._on_toggle     = on_notion_toggle
        self._on_ai_toggle  = on_ai_toggle
        self._on_settings   = on_open_settings
        self._env_path      = env_path
        self._notion_on     = False
        self._ai_on         = initial_ai
        self._collapsed     = False
        self._drag_x = self._drag_y = 0
        self._on_quit       = on_quit

        # ── Window ──────────────────────────────────────────────────────────
        self._win = tk.Toplevel(tk_root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.96)
        self._win.configure(bg=CHROMA)
        self._win.wm_attributes("-transparentcolor", CHROMA)
        self._win.resizable(False, False)

        sw = self._win.winfo_screenwidth()
        x  = initial_x if initial_x is not None else sw - DOCK_W_FULL - 20
        y  = initial_y if initial_y is not None else 40
        self._win.geometry(f"{DOCK_W_FULL}x{DOCK_H}+{x}+{y}")

        self._build_ui()

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self):
        cy = DOCK_H // 2

        # Canvas fills the window; CHROMA bg = transparent corners
        self._canvas = tk.Canvas(
            self._win, width=DOCK_W_FULL, height=DOCK_H,
            bg=CHROMA, highlightthickness=0,
        )
        self._canvas.place(x=0, y=0)

        # Pill background
        self._pill = self._canvas.create_polygon(
            _pill_pts(DOCK_W_FULL, DOCK_H), smooth=True,
            fill=DOCK_BG, outline="",
        )

        # Status dot
        self._dot = self._canvas.create_oval(
            DOT_CX - DOT_R, cy - DOT_R,
            DOT_CX + DOT_R, cy + DOT_R,
            fill=STATUS_IDLE, outline="",
        )

        # App label — drag handle
        self._label = tk.Label(
            self._win, text="murmr", bg=DOCK_BG, fg=DOCK_FG,
            font=("Segoe UI", 9, "bold"), cursor="fleur",
        )
        self._label.place(x=LABEL_X, y=0, width=LABEL_W, height=DOCK_H)

        # [AI] AI cleanup toggle
        _initial_ai_fg = AI_ON_FG if self._ai_on else AI_OFF_FG
        self._ai_btn = self._make_btn("AI", _initial_ai_fg, self._on_ai_click)
        self._ai_btn.place(x=BTN_L_X, y=0, width=26, height=DOCK_H)

        # [N] Notion toggle
        self._notion_btn = self._make_btn("N", NOTION_OFF_FG, self._on_notion_click)
        self._notion_btn.place(x=BTN_N_X, y=0, width=26, height=DOCK_H)

        # [⚙] Settings
        self._gear_btn = self._make_btn("⚙", DOCK_FG_DIM, self._on_settings,
                                        font=("Segoe UI", 10))
        self._gear_btn.place(x=BTN_G_X, y=0, width=26, height=DOCK_H)

        # [–] Minimize
        self._min_btn = self._make_btn("–", DOCK_FG_DIM, self._collapse)
        self._min_btn.place(x=BTN_MIN_X, y=0, width=26, height=DOCK_H)

        # [✕] Close — quits the app
        self._close_btn = self._make_btn("✕", DOCK_FG_DIM,
                                         lambda: self._on_quit() if self._on_quit else None)
        self._close_btn.place(x=BTN_X_X, y=0, width=26, height=DOCK_H)

        # [+] Expand (hidden in full mode)
        self._exp_btn = self._make_btn("+", DOCK_FG_DIM, self._expand)
        # placed only in collapsed mode

        # Drag bindings on canvas and label
        for w in (self._canvas, self._label):
            w.bind("<ButtonPress-1>",  self._drag_start)
            w.bind("<B1-Motion>",      self._drag_motion)
            w.bind("<ButtonRelease-1>", self._drag_end)

    def _make_btn(self, text, fg, command, font=None, cursor="hand2"):
        return tk.Button(
            self._win, text=text, bg=DOCK_BG, fg=fg,
            activebackground=DOCK_BTN_HOVER, activeforeground=fg,
            relief="flat", font=font or ("Segoe UI", 9, "bold"),
            cursor=cursor, command=command, bd=0,
        )

    # ── Collapse / expand ───────────────────────────────────────────────────

    def _collapse(self):
        self._collapsed = True

        # Resize window
        x, y = self._win.winfo_x(), self._win.winfo_y()
        self._win.geometry(f"{DOCK_W_MINI}x{DOCK_H}+{x}+{y}")

        # Resize canvas + redraw pill
        self._canvas.config(width=DOCK_W_MINI)
        self._canvas.coords(
            self._pill, _pill_pts(DOCK_W_MINI, DOCK_H),
        )

        # Hide full-mode widgets
        self._label.place_forget()
        self._ai_btn.place_forget()
        self._notion_btn.place_forget()
        self._gear_btn.place_forget()
        self._min_btn.place_forget()
        self._close_btn.place_forget()

        # Show expand button
        self._exp_btn.place(x=BTN_EXP_X, y=0, width=26, height=DOCK_H)

    def _expand(self):
        self._collapsed = False

        # Resize window
        x, y = self._win.winfo_x(), self._win.winfo_y()
        self._win.geometry(f"{DOCK_W_FULL}x{DOCK_H}+{x}+{y}")

        # Resize canvas + redraw pill
        self._canvas.config(width=DOCK_W_FULL)
        self._canvas.coords(
            self._pill, _pill_pts(DOCK_W_FULL, DOCK_H),
        )

        # Hide expand button
        self._exp_btn.place_forget()

        # Restore full-mode widgets
        self._label.place(x=LABEL_X, y=0, width=LABEL_W, height=DOCK_H)
        self._ai_btn.place(x=BTN_L_X, y=0, width=26, height=DOCK_H)
        self._notion_btn.place(x=BTN_N_X, y=0, width=26, height=DOCK_H)
        self._gear_btn.place(x=BTN_G_X, y=0, width=26, height=DOCK_H)
        self._min_btn.place(x=BTN_MIN_X, y=0, width=26, height=DOCK_H)
        self._close_btn.place(x=BTN_X_X, y=0, width=26, height=DOCK_H)

    # ── Drag ────────────────────────────────────────────────────────────────

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_motion(self, event):
        x = self._win.winfo_x() + (event.x - self._drag_x)
        y = self._win.winfo_y() + (event.y - self._drag_y)
        self._win.geometry(f"+{x}+{y}")

    def _drag_end(self, event):
        try:
            _write_env(self._env_path, {
                "DOCK_X": str(self._win.winfo_x()),
                "DOCK_Y": str(self._win.winfo_y()),
            })
        except Exception:
            pass

    # ── Button callbacks ────────────────────────────────────────────────────

    def _on_notion_click(self):
        if self._on_toggle:
            self._on_toggle()

    def _on_ai_click(self):
        if self._on_ai_toggle:
            self._on_ai_toggle()

    # ── Public API ──────────────────────────────────────────────────────────

    def update_status(self, state: str):
        """state: 'idle' | 'recording' | 'transcribing' | 'cleaning'"""
        color = {
            "idle":         STATUS_IDLE,
            "recording":    STATUS_REC,
            "transcribing": STATUS_BUSY,
            "cleaning":     STATUS_BUSY,
        }.get(state, STATUS_IDLE)
        self._canvas.itemconfig(self._dot, fill=color)
        self._win.lift()

    def update_notion_button(self, enabled: bool):
        self._notion_on = enabled
        self._notion_btn.config(fg=NOTION_ON_FG if enabled else NOTION_OFF_FG)

    def update_ai_button(self, enabled: bool):
        self._ai_on = enabled
        self._ai_btn.config(fg=AI_ON_FG if enabled else AI_OFF_FG)
