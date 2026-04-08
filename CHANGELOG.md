# Changelog

## v0.1.3 — 2026-04-08 — AI Cleanup (Phase 4)

### What's new

**AI-powered transcription cleanup**
- New `ai_cleaner.py` module — runs murmr's raw transcription output through OpenAI before paste
- Removes filler words: um, uh, ah, like (filler use), you know, basically, etc.
- Handles self-corrections: "encoder, sorry, decoder" → "decoder"; "Friday no Tuesdays" → "Tuesdays"
- Fixes subtle grammar errors and capitalisation artifacts
- Preserves the speaker's natural voice — no paraphrasing or summarising
- Falls back to raw transcription silently if the API call fails (transcription is never lost)
- Uses `gpt-4o-mini` by default — ~1–2s latency, low cost

**Dock [AI] button — now a live toggle**
- Click to enable/disable AI cleanup per session (same UX as [N] for Notion)
- Soft green = AI on, dim = AI off
- State syncs with Settings and tray menu

**Settings → AI section — now fully functional**
- "Enable AI cleanup" checkbox
- API Key field (masked)
- Model field (default `gpt-4o-mini`, editable)
- "Test Connection" button — validates the key with a live API ping
- Save writes `AI_ENABLED`, `OPENAI_API_KEY`, `OPENAI_MODEL` to `.env`

**Status dot — new "cleaning" state**
- Dot stays amber while AI cleanup is in progress (same colour as transcribing)

**Notion logging**
- Logs the cleaned text only (not raw output)

**Improved logging**
- `AI state: enabled=... key_present=... model=...` logged on every transcription
- `AI cleaned: "raw" → "cleaned"` logged on every successful cleanup
- API key changes via Settings take effect immediately — no restart needed

### Bug fix
- `config.OPENAI_API_KEY` was read once at startup — if you saved a key via Settings mid-session, AI cleanup silently skipped. Fixed: key/model are now live globals in `main.py`, updated immediately on Settings save.

### New file
- `murmr/ai_cleaner.py` — self-contained OpenAI cleanup module

### New `.env` keys
| Key | Default | What it controls |
|---|---|---|
| `AI_ENABLED` | `false` | Whether AI cleanup runs after transcription |
| `OPENAI_API_KEY` | _(empty)_ | Your OpenAI secret key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use for cleanup |

---

## v0.1.2 — 2026-04-08 — UI/UX Overhaul

### What's new

**Floating dock**
- Always-on-top draggable pill widget replaces the system tray as the primary UI surface
- Status dot: grey = idle, green = recording, amber = transcribing
- `[N]` button — instant Notion toggle (visual feedback: dim = off, blue = on)
- `[AI]` button — AI cleanup placeholder (coming soon, non-functional)
- `[⚙]` button — opens Settings window
- `[–]` / `[+]` buttons — collapse to a minimal dot-only view and expand back
- Drag anywhere on screen; position persists across restarts (saved to `.env`)
- True rounded corners via transparent chroma-key (same technique as the recording overlay)

**Settings window**
- Full GUI for all configuration — no more editing `.env` by hand
- **Notion section:** enable/disable toggle, Secret Key field (masked), page picker via Browse, Test Connection button
- **Browse pages:** fetches all Notion pages using your token and shows a scrollable picker — select to auto-fill Page ID and page name
- **AI section:** placeholder with disabled controls (coming soon)
- **Theme section:** Dark / Light toggle for the waveform overlay (applies on next recording)
- **Save button** — writes all changes to `.env` atomically
- Single-instance: re-opening focuses the existing window

**Two hotkey modes**
- `Ctrl+Win` — hands-free toggle: press once to start, press again to stop
- `Ctrl+Alt+Win` (hold) — push-to-talk: hold to record, release Win to transcribe
- 60 ms debounce on `Ctrl+Win` so a late-arriving Alt still correctly triggers PTT

**Waveform theme**
- Dark (default): black pill, white bars
- Light: light grey pill, dark bars
- Selected in Settings → saves to `.env` → applies from the next recording onward

**System tray updates**
- Icon turns **green** while recording (was red)
- Menu shows both "Notion logging" and "AI cleanup" (grayed placeholder)
- Notion checkbox stays in sync with dock and settings via `update_menu()`

### Bug fixes
- `.env` write: appending new keys to a file without a trailing newline no longer corrupts the previous value (e.g. `PAGE_ID=abcDOCK_X=1798`)
- Notion test connection: page IDs from Notion URLs (32-char hex, no hyphens) are now auto-formatted to UUID before calling `pages.retrieve()`
- Settings window height was too small — Save button was clipped off the bottom

### New files
- `murmr/dock.py` — floating mini-dock widget
- `murmr/settings_window.py` — settings GUI + `.env` read/write helpers
- `murmr/hotkeys.py` — extracted hotkey state machine (toggle + PTT modes)

### New `.env` keys
| Key | Default | What it controls |
|---|---|---|
| `OVERLAY_THEME` | `dark` | Waveform overlay colour scheme |
| `NOTION_PAGE_NAME` | _(empty)_ | Human-readable page name (set by Browse) |
| `DOCK_X` / `DOCK_Y` | _(screen edge)_ | Last saved dock position |

---

## v0.1.1 — 2026-04-07 — Notion Integration

### What's new

**Notion logging**
- Every transcription can be appended to a Notion page with a `YYYY-MM-DD HH:MM  →  text` timestamp format
- Off by default — toggle on/off from the tray icon: right-click → **Log to Notion** (checkmark = active)
- Runs in a background thread — paste is instant, Notion syncs a second later
- Tray notification if a Notion write fails (check `murmr.log` for details)
- Requires `NOTION_TOKEN` and `NOTION_PAGE_ID` in `murmr/.env`

**New files**
- `murmr/notion_writer.py` — all Notion API logic

---

## v0.1.0 — 2026-04-06 — Core (paste-to-cursor)

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
