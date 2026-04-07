# Changelog

## v1.1.0 — 2026-04-07 — Notion Integration

### What's new

**Notion logging (optional)**
- Every transcription can be appended to a Notion page with a `YYYY-MM-DD HH:MM  →  text` timestamp format
- Off by default — toggle on/off from the tray icon: right-click → **Log to Notion** (checkmark = active)
- Runs in a background thread — paste is instant, Notion syncs a second later
- Tray notification if a Notion write fails (check `murmr.log` for details)
- Requires `NOTION_TOKEN` and `NOTION_PAGE_ID` in `murmr/.env`

**New files**
- `murmr/notion_writer.py` — all Notion API logic

---

## v1.0.0 — 2026-04-06 — Core (paste-to-cursor)

### How it works
Press `Ctrl+Win` to start recording. A floating pill overlay appears at the bottom-centre of your screen with animated white bars that react to your voice. Press `Ctrl+Win` again to stop — bars dim while Whisper transcribes, then the overlay disappears and the text is pasted at your cursor.

### What's in it

**Hotkey**
- `Ctrl+Win` toggle (press once to start, press again to stop)
- Global — works from any app without losing cursor focus
- Debounced to prevent double-fire

**Floating overlay**
- 140×40px pill, black background (`#080808`), 88% alpha
- True transparent corners via `wm_attributes("-transparentcolor")`
- 7 white bars animated at 35ms — heights driven by live mic RMS
- Bars dim to dark grey during transcription, overlay destroys itself on paste

**System tray**
- "M" lettermark icon (PIL-drawn, no image file needed)
- Right-click → Quit to exit

**Launcher**
- `launch_murmr.bat` at project root — uses `pythonw.exe`, no terminal window
- Whisper model loads in a background thread so app is ready instantly

**Logging**
- All output to `murmr/murmr.log` with timestamps
- Includes faster-whisper's own debug output (model load, VAD, transcription detail)
