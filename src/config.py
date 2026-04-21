import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# --- Audio & Transcription ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")        # tiny | base | small
AUDIO_SAMPLERATE = int(os.getenv("AUDIO_SAMPLERATE", "16000"))
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")     # set to None for auto-detect

# --- Hotkey ---
HOTKEY_COMBO = os.getenv("HOTKEY_COMBO", "ctrl+win")

# --- Notion ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "")
NOTION_PAGE_NAME = os.getenv("NOTION_PAGE_NAME", "")

# --- AI Cleanup ---
AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"
AI_BACKEND = os.getenv("AI_BACKEND", "openai")             # openai | ollama
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1")

# --- UI ---
OVERLAY_THEME = os.getenv("OVERLAY_THEME", "dark")         # dark | light
DOCK_X = os.getenv("DOCK_X", "")
DOCK_Y = os.getenv("DOCK_Y", "")
