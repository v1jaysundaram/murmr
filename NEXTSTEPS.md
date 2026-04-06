# murmr — Next Steps

## Current status
Phase 1 core is working. The app transcribes speech and pastes text. Two issues to fix before it's fully usable as a standalone tool.

---

## Fix 1 — Standalone launcher (no terminal needed)

**Problem:** Running `python murmr/main.py` in VSCode means the app is tied to that terminal window.

**Fix:** Create `launch_murmr.bat` at the project root. Double-clicking it launches murmr silently with no window.

```bat
@echo off
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" murmr\main.py
```

`pythonw.exe` = Python without a console window. The `start ""` detaches the process so the .bat closes immediately after launching.

**To auto-start murmr when Windows boots:**
1. Press `Win+R`, type `shell:startup`, press Enter
2. Drop a shortcut to `launch_murmr.bat` in that folder
3. murmr will now start silently every time you log in

---

## Fix 2 — File logging (so you can debug without a terminal)

**Problem:** `print()` calls disappear when running with `pythonw.exe` — no console to show them.

**Fix:** Replace `print()` in `main.py` with Python's `logging` module, writing to `murmr/murmr.log`.

To check what murmr is doing, open `murmr/murmr.log` in any text editor.

---

## Fix 3 — Paste delay tweak

**Problem:** Paste might go to the wrong window if it fires too fast after hotkey release.

**Fix:** Increase `time.sleep(0.15)` → `time.sleep(0.3)` in the `do_paste()` function in `main.py`.

---

## Fix 4 — Update CLAUDE.md with launch instructions

Add a "How to run" section covering:
- Double-click `launch_murmr.bat` to start
- Right-click tray icon → Quit to stop
- Check `murmr/murmr.log` for logs
- Startup folder shortcut for auto-launch on login

---

## Verification (once fixes are done)

1. Double-click `launch_murmr.bat` — no window opens, grey circle appears in system tray
2. Open Notepad, click inside it so cursor is there
3. Hold `Ctrl+Shift+Space`, speak a sentence, release
4. Icon turns red → grey → text appears in Notepad
5. Open `murmr/murmr.log` — transcription should be logged there

---

## Phase 2 — Notion integration (after above is working)

1. Add `notion-client` to `requirements.txt`
2. Create `murmr/notion_writer.py` — appends timestamped text to a Notion page
3. Wire it into `main.py` — after paste, call `notion_writer.append_to_page(text)` in a background thread
4. Add `NOTION_TOKEN` and `NOTION_PAGE_ID` to `.env`
