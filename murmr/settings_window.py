"""
settings_window.py — Settings GUI for murmr.

Opens a tkinter Toplevel with three sections:
  - Notion: toggle, token, page ID (with Browse picker), test connection
  - AI: placeholder (disabled, coming soon)
  - Appearance: dark/light theme for the waveform overlay

Reads from and writes directly to the .env file.
"""

import logging
import os
import threading
import tkinter as tk
from tkinter import font as tkfont

from dotenv import dotenv_values

# ---------------------------------------------------------------------------
# Singleton guard
# ---------------------------------------------------------------------------
_win = None


# ---------------------------------------------------------------------------
# .env helpers
# ---------------------------------------------------------------------------

def _read_env(env_path: str) -> dict:
    """Return {KEY: value} from the .env file (empty dict if missing)."""
    if not os.path.exists(env_path):
        return {}
    return dict(dotenv_values(env_path))


def _write_env(env_path: str, updates: dict) -> None:
    """
    Merge `updates` into the .env file.
    Preserves comments and unknown keys. Replaces existing keys in-place.
    Appends new keys at the end. Writes atomically via os.replace().
    """
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    # Guard: if the last line has no trailing newline, appended keys would
    # concatenate directly onto it (e.g. "PAGE_ID=abcDOCK_X=1798").
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    written_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                written_keys.add(key)
                continue
        new_lines.append(line)

    for key, val in updates.items():
        if key not in written_keys:
            new_lines.append(f"{key}={val}\n")

    tmp_path = env_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.replace(tmp_path, env_path)


def _to_uuid(s: str) -> str:
    """
    Auto-format a bare 32-char hex string to UUID format.
    Notion page IDs from URLs look like: 1a2b3c4d5e6f... (no hyphens).
    The Notion API's pages.retrieve() requires: 1a2b3c4d-5e6f-...
    """
    s = s.strip().replace("-", "").replace(" ", "")
    if len(s) == 32 and all(c in "0123456789abcdefABCDEF" for c in s):
        return f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return s


# ---------------------------------------------------------------------------
# Notion page browser
# ---------------------------------------------------------------------------

def _open_page_browser(tk_root, token: str, page_id_var: tk.StringVar,
                       page_name_var: tk.StringVar,
                       BG, SECTION_BG, FG, FG_DIM, BTN_BG, ACCENT):
    """Fetch pages from Notion and open a picker dialog."""
    browser_win = tk.Toplevel(tk_root)
    browser_win.title("Choose a Notion Page")
    browser_win.resizable(False, False)
    browser_win.attributes("-topmost", True)
    browser_win.configure(bg=BG)

    sw = browser_win.winfo_screenwidth()
    sh = browser_win.winfo_screenheight()
    w, h = 360, 320
    browser_win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    tk.Label(browser_win, text="Your Notion pages", bg=BG, fg=FG,
             font=("Segoe UI", 10, "bold")).pack(pady=(14, 4), padx=16, anchor="w")

    status_var = tk.StringVar(value="Fetching pages…")
    status_lbl = tk.Label(browser_win, textvariable=status_var,
                          bg=BG, fg=FG_DIM, font=("Segoe UI", 8))
    status_lbl.pack(padx=16, anchor="w")

    list_frame = tk.Frame(browser_win, bg=SECTION_BG)
    list_frame.pack(fill="both", expand=True, padx=16, pady=6)

    scrollbar = tk.Scrollbar(list_frame, bg=SECTION_BG)
    scrollbar.pack(side="right", fill="y")

    listbox = tk.Listbox(
        list_frame, bg=SECTION_BG, fg=FG,
        selectbackground=ACCENT, selectforeground="#000000",
        font=("Segoe UI", 9), relief="flat",
        highlightthickness=0, activestyle="none",
        yscrollcommand=scrollbar.set,
    )
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)

    _page_ids = []  # list of (id, title) tuples

    def _select(event=None):
        sel = listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        pid, ptitle = _page_ids[idx]
        page_id_var.set(pid.replace("-", ""))   # store without hyphens
        page_name_var.set(ptitle)
        browser_win.destroy()

    listbox.bind("<Double-Button-1>", _select)
    listbox.bind("<Return>", _select)

    btn_frame = tk.Frame(browser_win, bg=BG)
    btn_frame.pack(fill="x", padx=16, pady=8)

    tk.Button(
        btn_frame, text="Select", command=_select,
        bg=ACCENT, fg="#000000", activebackground="#80d8ff",
        relief="flat", font=("Segoe UI", 9, "bold"),
        padx=14, pady=4, cursor="hand2",
    ).pack(side="right")

    tk.Button(
        btn_frame, text="Cancel", command=browser_win.destroy,
        bg=BTN_BG, fg=FG, activebackground="#444444",
        relief="flat", font=("Segoe UI", 9),
        padx=14, pady=4, cursor="hand2",
    ).pack(side="right", padx=(0, 6))

    def _fetch():
        try:
            from notion_client import Client
            client = Client(auth=token.strip())
            results = client.search(
                filter={"value": "page", "property": "object"},
                page_size=50,
            )
            pages = []
            for item in results.get("results", []):
                title = _extract_title(item)
                pages.append((item["id"], title))

            def _populate():
                if not browser_win.winfo_exists():
                    return
                if not pages:
                    status_var.set("No pages found.")
                    return
                status_var.set(f"{len(pages)} page(s) found — double-click or Select")
                for pid, ptitle in pages:
                    _page_ids.append((pid, ptitle))
                    listbox.insert("end", ptitle)

            browser_win.after(0, _populate)
        except Exception as e:
            def _err():
                if browser_win.winfo_exists():
                    status_var.set(f"Error: {e}")
            browser_win.after(0, _err)

    threading.Thread(target=_fetch, daemon=True).start()


def _extract_title(page: dict) -> str:
    """Pull the plain-text title out of a Notion page object."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            texts = prop.get("title", [])
            if texts:
                return texts[0].get("plain_text", "(Untitled)")
    # Fallback for databases / other structures
    return page.get("url", "(Untitled)").split("/")[-1][:60]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def open_settings(tk_root, get_notion_enabled, set_notion_enabled,
                  on_theme_change, env_path):
    """
    Open the settings window, or focus it if already open.

    tk_root:            main Tk root
    get_notion_enabled: callable() → bool
    set_notion_enabled: callable(bool)
    on_theme_change:    callable(theme: str)
    env_path:           absolute path to the .env file
    """
    global _win

    if _win is not None:
        try:
            _win.lift()
            _win.focus_force()
            return
        except tk.TclError:
            _win = None

    _win = tk.Toplevel(tk_root)
    _win.title("murmr Settings")
    _win.resizable(False, False)
    _win.attributes("-topmost", True)

    def _on_close():
        global _win
        _win.destroy()
        _win = None

    _win.protocol("WM_DELETE_WINDOW", _on_close)

    _win.update_idletasks()
    sw = _win.winfo_screenwidth()
    sh = _win.winfo_screenheight()
    w, h = 400, 490
    _win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Style ────────────────────────────────────────────────────────────────
    BG         = "#1e1e1e"
    SECTION_BG = "#2a2a2a"
    FG         = "#e0e0e0"
    FG_DIM     = "#888888"
    ACCENT     = "#4fc3f7"
    BTN_BG     = "#333333"

    _win.configure(bg=BG)

    def section_label(parent, text):
        lf = tk.Frame(parent, bg=BG)
        lf.pack(fill="x", padx=16, pady=(14, 2))
        tk.Label(lf, text=text, bg=BG, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Frame(lf, bg=SECTION_BG, height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

    def make_entry(parent, textvariable, show=None):
        return tk.Entry(
            parent, textvariable=textvariable,
            bg=BTN_BG, fg=FG, insertbackground=FG,
            relief="flat", font=("Segoe UI", 9), show=show,
        )

    def row_with_widget(parent, label_text, widget):
        f = tk.Frame(parent, bg=SECTION_BG)
        f.pack(fill="x", padx=16, pady=1)
        tk.Label(f, text=label_text, bg=SECTION_BG, fg=FG,
                 font=("Segoe UI", 9), width=10, anchor="w").pack(
            side="left", padx=(10, 4), pady=6)
        widget_parent = tk.Frame(f, bg=SECTION_BG)
        widget_parent.pack(side="left", fill="x", expand=True, padx=(0, 10))
        return widget_parent

    # ── Load .env ────────────────────────────────────────────────────────────
    env = _read_env(env_path)

    # ── NOTION SECTION ───────────────────────────────────────────────────────
    section_label(_win, "NOTION")

    notion_frame = tk.Frame(_win, bg=SECTION_BG)
    notion_frame.pack(fill="x", padx=16, pady=1)

    notion_var = tk.BooleanVar(value=get_notion_enabled())

    tk.Checkbutton(
        notion_frame, text="Enable Notion logging",
        variable=notion_var, bg=SECTION_BG, fg=FG,
        selectcolor=BTN_BG, activebackground=SECTION_BG,
        activeforeground=FG, font=("Segoe UI", 9),
    ).pack(anchor="w", padx=10, pady=(6, 2))

    token_var    = tk.StringVar(value=env.get("NOTION_TOKEN", ""))
    page_id_var  = tk.StringVar(value=env.get("NOTION_PAGE_ID", ""))
    page_name_var = tk.StringVar(value=env.get("NOTION_PAGE_NAME", ""))

    # Secret Key row
    f_token = tk.Frame(notion_frame, bg=SECTION_BG)
    f_token.pack(fill="x", padx=16, pady=1)
    tk.Label(f_token, text="Secret Key", bg=SECTION_BG, fg=FG,
             font=("Segoe UI", 9), width=10, anchor="w").pack(
        side="left", padx=(10, 4), pady=6)
    make_entry(f_token, token_var, show="●").pack(
        side="left", fill="x", expand=True, padx=(0, 10))

    # Page row — shows page name; user picks via Browse
    f_page = tk.Frame(notion_frame, bg=SECTION_BG)
    f_page.pack(fill="x", padx=16, pady=1)
    tk.Label(f_page, text="Page", bg=SECTION_BG, fg=FG,
             font=("Segoe UI", 9), width=10, anchor="w").pack(
        side="left", padx=(10, 4), pady=6)

    page_display_var = tk.StringVar()
    lbl_page = tk.Label(f_page, textvariable=page_display_var,
                        bg=SECTION_BG, fg=FG_DIM, font=("Segoe UI", 9), anchor="w")
    lbl_page.pack(side="left", fill="x", expand=True, padx=(0, 4))

    def _refresh_page_display(*_):
        name = page_name_var.get().strip()
        pid  = page_id_var.get().strip()
        if name:
            page_display_var.set(name)
            lbl_page.config(fg=FG)
        elif pid:
            short = (pid[:26] + "…") if len(pid) > 26 else pid
            page_display_var.set(short)
            lbl_page.config(fg=FG_DIM)
        else:
            page_display_var.set("Not selected")
            lbl_page.config(fg=FG_DIM)

    page_name_var.trace_add("write", _refresh_page_display)
    page_id_var.trace_add("write", _refresh_page_display)
    _refresh_page_display()

    tk.Button(
        f_page, text="Browse…",
        bg=BTN_BG, fg=FG, activebackground="#444444", activeforeground=FG,
        relief="flat", font=("Segoe UI", 8), padx=6, pady=2, cursor="hand2",
        command=lambda: _open_page_browser(
            _win, token_var.get(), page_id_var, page_name_var,
            BG, SECTION_BG, FG, FG_DIM, BTN_BG, ACCENT,
        ),
    ).pack(side="left", padx=(0, 10), pady=4)

    # Test connection row
    test_frame = tk.Frame(notion_frame, bg=SECTION_BG)
    test_frame.pack(fill="x", padx=10, pady=(4, 8))

    conn_status_var = tk.StringVar(value="")
    conn_label = tk.Label(test_frame, textvariable=conn_status_var,
                          bg=SECTION_BG, fg=FG_DIM, font=("Segoe UI", 8),
                          wraplength=240, justify="left")
    conn_label.pack(side="right", padx=(8, 0))

    def _run_test():
        conn_status_var.set("Testing…")
        conn_label.config(fg=FG_DIM)
        token   = token_var.get().strip()
        page_id = _to_uuid(page_id_var.get().strip())

        def _worker():
            try:
                from notion_client import Client
                client = Client(auth=token)
                client.pages.retrieve(page_id)
                result, color = "Connected ✓", "#4caf50"
            except Exception as e:
                short = str(e)[:120]
                result, color = f"Failed: {short}", "#f44336"
            if _win and _win.winfo_exists():
                _win.after(0, lambda: (
                    conn_status_var.set(result),
                    conn_label.config(fg=color),
                ))

        threading.Thread(target=_worker, daemon=True).start()

    tk.Button(
        test_frame, text="Test Connection", command=_run_test,
        bg=BTN_BG, fg=FG, activebackground="#444444", activeforeground=FG,
        relief="flat", font=("Segoe UI", 9), padx=8, pady=3, cursor="hand2",
    ).pack(side="left")

    # ── AI SECTION (placeholder) ─────────────────────────────────────────────
    section_label(_win, "AI  (coming soon)")

    llm_frame = tk.Frame(_win, bg=SECTION_BG)
    llm_frame.pack(fill="x", padx=16, pady=1)

    tk.Checkbutton(
        llm_frame, text="Enable AI cleanup",
        bg=SECTION_BG, fg=FG_DIM, selectcolor=BTN_BG,
        activebackground=SECTION_BG, activeforeground=FG_DIM,
        font=("Segoe UI", 9), state="disabled",
    ).pack(anchor="w", padx=10, pady=(6, 2))

    for label_text, placeholder in [("Model", "e.g. claude-sonnet-4-6"),
                                     ("API Key", "sk-ant-…")]:
        f = tk.Frame(llm_frame, bg=SECTION_BG)
        f.pack(fill="x", padx=16, pady=1)
        tk.Label(f, text=label_text, bg=SECTION_BG, fg=FG_DIM,
                 font=("Segoe UI", 9), width=10, anchor="w").pack(
            side="left", padx=(10, 4), pady=6)
        e = tk.Entry(f, bg=BTN_BG, fg=FG_DIM, relief="flat",
                     font=("Segoe UI", 9), state="disabled")
        e.pack(side="left", fill="x", expand=True, padx=(0, 10))


    # ── THEME SECTION ────────────────────────────────────────────────────────
    section_label(_win, "THEME")

    appear_frame = tk.Frame(_win, bg=SECTION_BG)
    appear_frame.pack(fill="x", padx=16, pady=1)

    current_theme = env.get("OVERLAY_THEME", "dark")
    theme_var = tk.StringVar(value=current_theme)

    theme_row = tk.Frame(appear_frame, bg=SECTION_BG)
    theme_row.pack(anchor="w", padx=10, pady=(6, 2))
    tk.Label(theme_row, text="Waveform:", bg=SECTION_BG, fg=FG,
             font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))
    for val, label in [("dark", "Dark"), ("light", "Light")]:
        tk.Radiobutton(
            theme_row, text=label, variable=theme_var, value=val,
            bg=SECTION_BG, fg=FG, selectcolor=BTN_BG,
            activebackground=SECTION_BG, activeforeground=FG,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=4)


    # ── SAVE ─────────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(_win, bg=BG)
    btn_frame.pack(fill="x", padx=16, pady=14)

    save_status_var = tk.StringVar(value="")
    tk.Label(btn_frame, textvariable=save_status_var, bg=BG, fg="#4caf50",
             font=("Segoe UI", 8)).pack(side="left")

    def _save():
        updates = {
            "NOTION_TOKEN":    token_var.get().strip(),
            "NOTION_PAGE_ID":  page_id_var.get().strip(),
            "NOTION_PAGE_NAME": page_name_var.get().strip(),
            "OVERLAY_THEME":   theme_var.get(),
        }
        try:
            _write_env(env_path, updates)
            logging.info("Settings written to .env: %s", list(updates.keys()))
        except Exception as e:
            logging.error("Settings save failed: %s", e)
            save_status_var.set(f"Save failed: {e}")
            return

        set_notion_enabled(notion_var.get())
        on_theme_change(theme_var.get())
        save_status_var.set("Saved ✓")
        if _win and _win.winfo_exists():
            _win.after(3000, lambda: save_status_var.set("") if _win else None)

    tk.Button(
        btn_frame, text="Save", command=_save,
        bg=ACCENT, fg="#000000", activebackground="#80d8ff",
        relief="flat", font=("Segoe UI", 10, "bold"),
        padx=28, pady=6, cursor="hand2",
    ).pack(side="right")
