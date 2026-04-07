# murmr

A local-first voice dictation app for Windows. Lives in the system tray. Press a hotkey to record, press again to transcribe, and your spoken words are pasted wherever your cursor is. Optionally logs transcriptions to a Notion page.

---

## What this app does

1. Sits silently in the Windows system tray (bottom-right corner)
2. You press `Ctrl+Win` to start recording
3. A floating pill overlay appears at the bottom of your screen with animated bars — so you always know recording is active
4. You press `Ctrl+Win` again when done
5. The app transcribes your speech locally using AI (no internet needed for this part)
6. The transcribed text is pasted at your cursor — works in any app
7. (Phase 2) The text is also appended to a Notion page with a timestamp

---

## Why we're building it this way

- **Local transcription** — faster-whisper runs on your machine. No audio ever leaves your computer. Zero cost per transcription.
- **System tray** — always available without cluttering your taskbar or desktop.
- **Hotkey-driven** — no clicking, no switching windows. Just press and speak.
- **Floating overlay** — clear visual feedback while recording without a persistent window.
- **Notion for memory** — a running log of everything you've dictated, organized by time.

---

## Tech stack

| Library | What it does |
|---|---|
| `faster-whisper` | Transcribes audio to text locally using a small AI model |
| `pynput` | Detects the global Ctrl+Win hotkey (works across all apps) |
| `sounddevice` | Captures audio from your microphone + provides live RMS level |
| `pyperclip` | Copies text to the clipboard |
| `pystray` | System tray icon — background presence + Quit menu |
| `tkinter` | Built-in Python UI — draws the floating recording overlay |
| `Pillow` | Draws the tray icon "M" lettermark in memory (no icon file needed) |
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
├── recorder.py           ← handles microphone recording + live RMS level
├── transcriber.py        ← converts audio to text using faster-whisper
├── main.py               ← tray icon, hotkey, floating overlay, orchestration
└── notion_writer.py      ← (Phase 2) sends transcriptions to Notion
launch_murmr.bat          ← double-click to start (no terminal window)
```

---

## Build phases

### Phase 1 — Core (paste-to-cursor) ✓
End-to-end flow working: press hotkey → record → transcribe → paste.

### Phase 2 — Notion integration ✓
`notion_writer.py` logs every transcription to a Notion page with a timestamp. Toggled on/off from the tray icon (off by default). Requires `NOTION_TOKEN` and `NOTION_PAGE_ID` in `.env`.

---

## Settings (configured in `.env`)

| Variable | Default | What it controls |
|---|---|---|
| `WHISPER_MODEL` | `small` | AI model size. Options: `tiny`, `base`, `small`. Smaller = faster but less accurate. |
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

## How to run

- **Start:** Double-click `launch_murmr.bat` — app starts silently in the system tray
- **Record:** Press `Ctrl+Win` to start — a floating pill overlay appears at bottom-centre of your screen with animated bars
- **Stop:** Press `Ctrl+Win` again — bars dim while transcribing, overlay disappears, text pastes at cursor
- **Quit:** Right-click the tray icon → Quit
- **Logs:** Check `murmr/murmr.log` to see what the app is doing (transcriptions, errors, model output)
- **Auto-start on login:** Press `Win+R` → type `shell:startup` → drop a shortcut to `launch_murmr.bat` in that folder

---

## Known gotchas

- `sounddevice` requires PortAudio to be installed on Windows. If you get an error about PortAudio, run: `pip install sounddevice` and if that fails, use `conda install -c conda-forge portaudio`.
- `pynput` global hotkeys may not work in apps running as Administrator (like some games or elevated terminals). Run `murmr` as Administrator in those cases.
- The first time `transcriber.py` runs, faster-whisper will download the model weights (~500MB for `small`). This only happens once — subsequent runs are instant.
- Pasting works by copying text to clipboard then simulating `Ctrl+V`. This briefly overwrites your clipboard. This is a known limitation.
- The floating overlay uses `wm_attributes("-transparentcolor")` for true rounded corners — this requires Windows 10/11.
