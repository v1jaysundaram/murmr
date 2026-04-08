import os
from dotenv import load_dotenv

# Load the .env file from the same folder as this script.
# If .env doesn't exist, the app still runs using the defaults below.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# --- Audio & Transcription ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
AUDIO_SAMPLERATE = int(os.getenv("AUDIO_SAMPLERATE", "16000"))
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")  # set to None for auto-detect

# --- Notion (Phase 2) ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "")

# --- AI Cleanup (Phase 4) ---
AI_ENABLED    = os.getenv("AI_ENABLED", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- UI ---
OVERLAY_THEME = os.getenv("OVERLAY_THEME", "dark")
DOCK_X = os.getenv("DOCK_X", "")
DOCK_Y = os.getenv("DOCK_Y", "")
