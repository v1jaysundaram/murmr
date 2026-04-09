# murmr

A local-first voice dictation app for Windows. Press a hotkey, speak, press again — your words are pasted wherever your cursor is. Runs entirely on your machine. No cloud, no subscription.

---

## Features

- **Hotkey-driven** — `Ctrl+Win` to toggle, or hold `Ctrl+Alt+Win` for push-to-talk
- **Local transcription** — powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper); audio never leaves your machine
- **Parallel transcription** — silence detection splits speech mid-recording so segments transcribe in the background; only the final chunk waits on stop
- **AI cleanup** — optional pass to strip fillers, fix grammar, handle self-corrections (OpenAI or local Ollama)
- **Floating dock** — draggable always-on-top pill with live status; position persists
- **System tray** — background presence, right-click menu
- **Notion logging** — optionally appends every transcription to a Notion page with a timestamp
- **Settings GUI** — no `.env` editing required; everything configurable in-app

---

## How it works

```
Hotkey press
    └── recorder.py     starts mic stream, emits silence-split segments to queue
         └── main.py    segment worker transcribes each chunk in background
              └── transcriber.py   faster-whisper inference
                   └── ai_cleaner.py   (optional) filler/grammar cleanup
                        └── main.py    paste at cursor via clipboard + Ctrl+V
                             └── notion_writer.py   (optional) append to Notion
```

On stop, only the final (unfinished) segment remains to be transcribed. Everything before it is already done.

---

## Folder structure

```
murmr/
├── murmr.bat               — launcher (double-click; no terminal window)
├── CHANGELOG.md
├── README.md
└── src/
    ├── main.py             — orchestration: tray, overlay, recording flow
    ├── dock.py             — floating dock widget
    ├── hotkeys.py          — global hotkey listener (pynput)
    ├── recorder.py         — mic capture + silence-based segment splitting
    ├── transcriber.py      — faster-whisper wrapper
    ├── ai_cleaner.py       — AI cleanup (OpenAI + Ollama)
    ├── notion_writer.py    — Notion page appender
    ├── settings_window.py  — settings GUI + .env read/write
    ├── config.py           — loads .env, exports all settings
    ├── .env                — your secrets and preferences (never commit this)
    ├── .env.example        — safe template
    ├── requirements.txt    — Python dependencies
    └── murmr.log           — runtime log (auto-rotated, max 512KB)
```

---

## Requirements

- Windows 10 or 11
- Python 3.10+
- A microphone

---

## Setup

**1. Clone and install dependencies**

```bash
git clone https://github.com/your-username/murmr.git
cd murmr
python -m venv .venv
.venv\Scripts\activate
pip install -r src/requirements.txt
```

**2. Create your config**

```bash
copy src\.env.example src\.env
```

Edit `src\.env` — at minimum, set `WHISPER_MODEL`. Everything else is optional.

**3. Run**

Double-click `murmr.bat`, or:

```bash
cd src
python main.py
```

The dock appears in the top-right corner. The tray icon confirms it's running.

> **First run:** faster-whisper will download model weights (~500MB for `small`). This only happens once.

---

## Usage

| Action | How |
|---|---|
| Start recording | `Ctrl+Win` |
| Stop and paste | `Ctrl+Win` again |
| Push-to-talk | Hold `Ctrl+Alt+Win`, release to transcribe |
| Toggle Notion logging | Click `[N]` on dock, or tray → Notion logging |
| Toggle AI cleanup | Click `[AI]` on dock, or tray → AI cleanup |
| Open settings | Click `[⚙]` on dock, or tray → Settings |
| Collapse dock | Click `[–]` on dock |
| Quit | Click `[✕]` on dock, or tray → Quit |

**Auto-start on login:** `Win+R` → `shell:startup` → drop a shortcut to `murmr.bat`

---

## Configuration

All settings are editable in the Settings window or directly in `src/.env`.

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `small` | Model size: `tiny`, `base`, `small` |
| `AUDIO_SAMPLERATE` | `16000` | Sample rate (16000 Hz is what Whisper expects) |
| `WHISPER_LANGUAGE` | `en` | Transcription language; leave blank for auto-detect |
| `AI_ENABLED` | `false` | Run AI cleanup after transcription |
| `AI_BACKEND` | `openai` | `openai` or `ollama` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model for cleanup |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model (run `ollama pull llama3.2:3b` first) |
| `OLLAMA_ENDPOINT` | `http://localhost:11434/v1` | Ollama API endpoint |
| `OVERLAY_THEME` | `dark` | Waveform overlay theme: `dark` or `light` |
| `NOTION_TOKEN` | — | Notion API integration token |
| `NOTION_PAGE_ID` | — | ID of the Notion page to log to |

---

## Gotchas

- **PortAudio error** — run `pip install sounddevice` or `conda install -c conda-forge portaudio`
- **Hotkeys not working in elevated apps** — run murmr as Administrator
- **Pasting overwrites clipboard briefly** — the previous clipboard contents are restored ~100ms after paste
- **Overlay theme changes** take effect on the next recording, not the current one
- **`pynput` hotkeys** may conflict with some games or apps that hook keyboard input at a low level

---

## License

MIT — do whatever you want with it.
