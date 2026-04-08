# murmr

A local-first voice dictation app for Windows. Lives in the system tray and a floating dock. Press a hotkey to record, press again to transcribe, and your spoken words are pasted wherever your cursor is. Optionally logs transcriptions to a Notion page.

---

## What this app does

1. Sits silently in the Windows system tray + shows a small floating dock in the corner
2. Press `Ctrl+Win` to start recording (hands-free toggle)
3. A floating pill overlay appears at the bottom of your screen with animated bars
4. Press `Ctrl+Win` again when done — OR hold `Ctrl+Alt+Win` for push-to-talk (release to transcribe)
5. The app transcribes your speech locally using AI (no internet needed for this part)
6. The transcribed text is pasted at your cursor — works in any app
7. Optionally appended to a Notion page with a timestamp

---

## Why we're building it this way

- **Local transcription** — faster-whisper runs on your machine. No audio ever leaves your computer. Zero cost per transcription.
- **Floating dock** — always-visible mini widget replaces the system tray as the primary UI. Draggable, collapsible.
- **Hotkey-driven** — no clicking, no switching windows. Just press and speak.
- **Floating overlay** — clear visual feedback while recording without a persistent window.
- **Settings GUI** — full configuration window, no `.env` editing needed.
- **Notion for memory** — a running log of everything you've dictated, organized by time.

---

## Tech stack

| Library | What it does |
|---|---|
| `faster-whisper` | Transcribes audio to text locally using a small AI model |
| `pynput` | Detects global hotkeys (works across all apps) |
| `sounddevice` | Captures audio from your microphone + provides live RMS level |
| `pyperclip` | Copies text to the clipboard |
| `pystray` | System tray icon — background presence + menu |
| `tkinter` | Built-in Python UI — floating overlay, dock, settings window |
| `Pillow` | Draws the tray icon "M" lettermark in memory (no icon file needed) |
| `python-dotenv` | Loads settings from a `.env` file |
| `numpy` | Handles raw audio data as arrays |
| `notion-client` | Sends text to your Notion page |

---

## File map

```
src/                      ← the actual app code lives here
├── .env                  ← your personal settings + secrets (never share this)
├── .env.example          ← a safe template showing what .env should look like
├── requirements.txt      ← list of libraries to install
├── config.py             ← reads .env and makes settings available to all files
├── recorder.py           ← handles microphone recording + live RMS level
├── transcriber.py        ← converts audio to text using faster-whisper
├── hotkeys.py            ← global hotkey listener (toggle + push-to-talk modes)
├── dock.py               ← floating mini-dock widget (status, toggles, settings)
├── settings_window.py    ← settings GUI + .env read/write helpers
├── main.py               ← tray icon, overlay, orchestration, wires everything
├── notion_writer.py      ← sends transcriptions to Notion
├── ai_cleaner.py         ← AI cleanup pass (fillers, grammar, self-corrections) — supports OpenAI and Ollama
└── murmr.log             ← runtime log (transcriptions, errors, model output)
murmr.bat                 ← double-click to start (no terminal window)
```

---

## Build phases

### Phase 1 — Core (paste-to-cursor) ✓
End-to-end flow working: press hotkey → record → transcribe → paste.

### Phase 2 — Notion integration ✓
`notion_writer.py` logs every transcription to a Notion page with a timestamp.

### Phase 3 — UI/UX overhaul ✓
Floating dock, settings window, push-to-talk hotkey, waveform themes, tray sync.

### Phase 4 — AI cleanup ✓
After transcription, runs text through an AI model to remove fillers, fix grammar, and handle self-corrections before pasting. Toggle via dock `[AI]` button or Settings.

### Phase 5 — Ollama integration ✓
Settings → AI now offers a backend selector: **OpenAI** (cloud) or **Ollama (local)**. Ollama runs fully on-device — no API key, no internet. Recommended model: `llama3.2:3b` (`ollama pull llama3.2:3b`).

---

## Settings (configured in Settings window or `.env`)

| Variable | Default | What it controls |
|---|---|---|
| `WHISPER_MODEL` | `small` | AI model size. Options: `tiny`, `base`, `small`. |
| `AUDIO_SAMPLERATE` | `16000` | Recording quality. 16000 Hz is what Whisper expects. |
| `NOTION_TOKEN` | _(empty)_ | Your Notion API secret key. |
| `NOTION_PAGE_ID` | _(empty)_ | The ID of the Notion page to log to. |
| `NOTION_PAGE_NAME` | _(empty)_ | Human-readable page name (set automatically via Browse). |
| `OVERLAY_THEME` | `dark` | Waveform overlay theme: `dark` or `light`. |
| `DOCK_X` / `DOCK_Y` | _(screen edge)_ | Last saved dock position (set automatically by dragging). |
| `AI_ENABLED` | `false` | Whether AI cleanup runs after transcription. |
| `AI_BACKEND` | `openai` | Which backend to use: `openai` or `ollama`. |
| `OPENAI_API_KEY` | _(empty)_ | Your OpenAI secret key. |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model used for cleanup. |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model to use (must be pulled first). |
| `OLLAMA_ENDPOINT` | `http://localhost:11434/v1` | Ollama API endpoint. |

---

## Rules for building this project

- **One file at a time.** Build, explain, test, confirm — then move to the next file.
- **Never hardcode secrets.** API tokens and personal settings go in `.env`, never in `.py` files.
- **Plain-English explanations.** Each file gets a short explanation of what it does and why.
- **Wait for confirmation** before moving to the next step.

---

## How to run

- **Start:** Double-click `murmr.bat` — app starts silently; dock appears in top-right corner
- **Hands-free:** Press `Ctrl+Win` to start → speak → press `Ctrl+Win` again to stop and paste
- **Push-to-talk:** Hold `Ctrl+Alt+Win` while speaking → release Win key to transcribe and paste
- **Notion toggle:** Click `[N]` on the dock, or right-click tray → Notion logging
- **Settings:** Click `[⚙]` on the dock, or right-click tray → Settings
- **Collapse dock:** Click `[–]` on the dock to shrink it; `[+]` to expand
- **Quit:** Right-click the tray icon → Quit
- **Logs:** Check `src/murmr.log` to see what the app is doing
- **Auto-start on login:** Press `Win+R` → type `shell:startup` → drop a shortcut to `murmr.bat`

---

## Known gotchas

- `sounddevice` requires PortAudio on Windows. If you get an error: `pip install sounddevice` or `conda install -c conda-forge portaudio`.
- `pynput` global hotkeys may not work in apps running as Administrator. Run `murmr` as Administrator in those cases.
- The first time `transcriber.py` runs, faster-whisper downloads model weights (~500MB for `small`). This only happens once.
- Pasting works by copying text to clipboard then simulating `Ctrl+V`. This briefly overwrites your clipboard.
- The floating overlay and dock use `wm_attributes("-transparentcolor")` for true rounded corners — requires Windows 10/11.
- Waveform theme changes apply on the **next recording**, not the currently open overlay.
- If the `.env` file's NOTION_PAGE_ID becomes corrupted, re-enter it via Settings → Browse.
