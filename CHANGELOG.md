# Changelog

## [1.0.0] — 2026-04-09
### Added
- Parallel transcription — sentences transcribed in the background while you speak; only the final segment waits on stop. Noticeably faster for anything longer than ~5s.
- Clipboard restore — previous clipboard contents are saved before pasting and restored immediately after.
- Dock loading state — status dot turns amber while Whisper loads on startup, so you know when it's ready.
- Log rotation — `murmr.log` capped at 512KB with 3 backups; no more unbounded growth.

---

## [0.1.5] — 2026-04-09
### Added
- Dock `[✕]` close button — quits the app

### Changed
- AI cleanup defaults to off
- AI prompt shortened ~60% — same quality, faster inference, lower cost
- OpenAI and Ollama clients cached per session (eliminates per-call TCP overhead)
- Notion client cached per session
- Source folder renamed `murmr/` → `src/`

---

## [0.1.4] — 2026-04-09
### Added
- Ollama as a local AI backend (no API key, no internet required)
- Settings → AI: backend selector, Ollama model + endpoint fields, Test Connection

---

## [0.1.3] — 2026-04-08
### Added
- AI cleanup pass after transcription (filler removal, grammar, self-corrections)
- Dock `[AI]` live toggle; status dot "cleaning" state
- Settings → AI section (enable, API key, model, Test Connection)

### Fixed
- OpenAI key/model changes via Settings now apply immediately without restart

---

## [0.1.2] — 2026-04-08
### Added
- Floating dock — draggable pill, always-on-top, position persists
- Settings window GUI — no more editing `.env` by hand
- Push-to-talk mode (`Ctrl+Alt+Win`)
- Waveform theme switcher (dark / light)

### Fixed
- `.env` write no longer corrupts adjacent keys when appending new ones
- Notion test: URL-style page IDs auto-formatted to UUID
- Settings window height clipped the Save button

---

## [0.1.1] — 2026-04-07
### Added
- Notion integration — logs every transcription to a page with timestamp

---

## [0.1.0] — 2026-04-06
### Added
- Core dictation loop: hotkey → record → Whisper → paste at cursor
- Floating waveform overlay with live RMS animation
- System tray icon with Quit
- `murmr.bat` launcher (no terminal window)
