# murmr

A local-first voice dictation app for Windows. Lives in the system tray. Hold a hotkey to record, release to transcribe, and your spoken words are pasted wherever your cursor is. Optionally logs transcriptions to a Notion page.

---

## What this app does

1. Sits silently in the Windows system tray (bottom-right corner)
2. You hold `Ctrl+Shift+Space` while speaking
3. You release the hotkey when done
4. The app transcribes your speech locally using AI (no internet needed for this part)
5. The transcribed text is pasted at your cursor — works in any app
6. (Phase 2) The text is also appended to a Notion page with a timestamp

---

## Why we're building it this way

- **Local transcription** — faster-whisper runs on your machine. No audio ever leaves your computer. Zero cost per transcription.
- **System tray** — always available without cluttering your taskbar or desktop.
- **Hotkey-driven** — no clicking, no switching windows. Just hold and speak.
- **Notion for memory** — a running log of everything you've dictated, organized by time.

---

## Tech stack

| Library | What it does |
|---|---|
| `faster-whisper` | Transcribes audio to text locally using a small AI model |
| `pynput` | Detects global keyboard shortcuts (works across all apps) |
| `sounddevice` | Captures audio from your microphone |
| `soundfile` | Reads/writes audio files |
| `pyperclip` | Copies text to the clipboard |
| `pystray` | Creates the system tray icon |
| `Pillow` | Draws the tray icon image in memory (no icon file needed) |
| `python-dotenv` | Loads settings from a `.env` file |
| `numpy` | Handles raw audio data as arrays |
| `notion-client` | (Phase 2) Sends text to your Notion page |

---

## File map

```
murmr/                    ← the actual app code lives here
├── .env                  ← your personal settings + secrets (never share this)
├── .env.example          ← a safe template showing what .env should look like
├── requirements.txt      ← list of libraries to install
├── config.py             ← reads .env and makes settings available to all files
├── recorder.py           ← handles microphone recording
├── transcriber.py        ← converts audio to text using faster-whisper
├── main.py               ← the main program: tray icon, hotkey, orchestration
└── notion_writer.py      ← (Phase 2) sends transcriptions to Notion
```

---

## Build phases

### Phase 1 — Core (paste-to-cursor)
Get the end-to-end flow working: hold hotkey → record → transcribe → paste.
No Notion, no internet required.

**Build order:**
1. `requirements.txt` — install dependencies
2. `config.py` + `.env.example` — settings setup
3. `recorder.py` — microphone capture
4. `transcriber.py` — speech-to-text
5. `main.py` — put it all together

### Phase 2 — Notion integration
Wire up `notion_writer.py` and connect it in `main.py` so transcriptions are also logged.

---

## Settings (configured in `.env`)

| Variable | Default | What it controls |
|---|---|---|
| `WHISPER_MODEL` | `small` | AI model size. Options: `tiny`, `base`, `small`. Smaller = faster but less accurate. |
| `HOTKEY_COMBO` | `ctrl+shift+space` | The key combination to hold while speaking. |
| `AUDIO_SAMPLERATE` | `16000` | Recording quality. 16000 Hz is what Whisper expects — don't change this. |
| `NOTION_TOKEN` | _(empty)_ | Your Notion API key. Only needed for Phase 2. |
| `NOTION_PAGE_ID` | _(empty)_ | The ID of the Notion page to log to. Only needed for Phase 2. |

---

## Rules for building this project

- **One file at a time.** Build, explain, test, confirm — then move to the next file.
- **Never hardcode secrets.** API tokens and personal settings go in `.env`, never in `.py` files.
- **Plain-English explanations.** Each file gets a short explanation of what it does and why.
- **Wait for confirmation** before moving to the next step.

---

## Known gotchas

- `sounddevice` requires PortAudio to be installed on Windows. If you get an error about PortAudio, run: `pip install sounddevice` and if that fails, download the PortAudio DLL from [portaudio.com](http://www.portaudio.com/) or use `conda install -c conda-forge portaudio`.
- `pynput` global hotkeys may not work in apps running as Administrator (like some games or elevated terminals). Run `murmr` as Administrator in those cases.
- The first time `transcriber.py` runs, faster-whisper will download the model weights (~500MB for `small`). This only happens once — subsequent runs are instant.
- Pasting works by copying text to clipboard then simulating `Ctrl+V`. This briefly overwrites your clipboard. This is a known limitation.
