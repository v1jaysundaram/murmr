# Changelog

## Current build — 2026-04-06

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
