import os
from dotenv import load_dotenv

# Load the .env file from the same folder as this script.
# If .env doesn't exist, the app still runs using the defaults below.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# --- Audio & Transcription ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
AUDIO_SAMPLERATE = int(os.getenv("AUDIO_SAMPLERATE", "16000"))

# --- Hotkey ---
HOTKEY_COMBO = os.getenv("HOTKEY_COMBO", "ctrl+shift+space")

# --- Notion (Phase 2) ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "")
