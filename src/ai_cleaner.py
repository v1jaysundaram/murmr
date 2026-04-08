"""
ai_cleaner.py — AI-powered transcription cleanup for murmr.

Takes raw Whisper output and runs it through OpenAI to:
  - Remove filler words (um, uh, ah, like, you know, etc.)
  - Handle self-corrections ("Hey Mark, sorry, John!" → "Hey John!")
  - Fix subtle grammar errors that Whisper may have introduced
  - Preserve the speaker's natural voice and intent

Falls back to the raw transcription if anything goes wrong — the
transcription is never lost due to an API failure.
"""

import logging

import openai

# ---------------------------------------------------------------------------
# Prompt + inference settings
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a transcription cleanup assistant. Clean raw speech-to-text output:

1. REMOVE filler words: um, uh, ah, er, hmm, like, you know, basically, \
literally, right, kind of, sort of (when used as fillers with no meaning).

2. HANDLE self-corrections: keep only the final intended version. Remove \
false starts and correction markers (sorry, wait, no, I mean, actually, \
scratch that).
   E.g. "Send it to Mark, sorry, John" → "Send it to John"
   E.g. "Schedule it for Monday, wait, Tuesday" → "Schedule it for Tuesday"

3. FIX speech-to-text artifacts: run-on words, missing capitalization, \
obvious mishears. Keep informal grammar intact — preserve the speaker's voice.

4. NEVER paraphrase, summarize, or change meaning.

5. Return cleaned text only. No explanation, no quotes."""

MAX_TOKENS  = 500
TEMPERATURE = 0.1

# ---------------------------------------------------------------------------
# Client cache — reused across calls to avoid per-call TCP setup overhead
# ---------------------------------------------------------------------------

_openai_client: openai.OpenAI | None = None
_openai_client_key: str = ""

_ollama_client: openai.OpenAI | None = None
_ollama_client_endpoint: str = ""


def _get_openai_client(api_key: str) -> openai.OpenAI:
    global _openai_client, _openai_client_key
    if _openai_client is None or _openai_client_key != api_key:
        _openai_client     = openai.OpenAI(api_key=api_key)
        _openai_client_key = api_key
    return _openai_client


def _get_ollama_client(endpoint: str) -> openai.OpenAI:
    global _ollama_client, _ollama_client_endpoint
    if _ollama_client is None or _ollama_client_endpoint != endpoint:
        _ollama_client          = openai.OpenAI(api_key="ollama", base_url=endpoint)
        _ollama_client_endpoint = endpoint
    return _ollama_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_transcription(text: str, api_key: str, model: str = "gpt-4o-mini") -> str:
    """
    Clean up a raw Whisper transcription using OpenAI.

    Returns the cleaned text, or the original text if the API call fails.
    Never raises — failures are logged and the raw transcription is preserved.
    """
    if not text.strip():
        return text

    try:
        client   = _get_openai_client(api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": text},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        cleaned = response.choices[0].message.content.strip()
        if cleaned:
            logging.info("AI cleaned: %r → %r", text, cleaned)
            return cleaned
        logging.warning("AI returned empty response — using raw transcription.")
        return text

    except Exception as e:
        logging.error("AI cleanup failed (%s) — using raw transcription.", e)
        return text


def clean_transcription_ollama(text: str, model: str = "llama3.2:3b",
                                endpoint: str = "http://localhost:11434/v1") -> str:
    """
    Clean up a raw Whisper transcription using a locally running Ollama model.

    Uses Ollama's OpenAI-compatible API — no internet or API key required.
    Falls back to the raw transcription if Ollama is unreachable or fails.
    """
    if not text.strip():
        return text

    try:
        client   = _get_ollama_client(endpoint)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": text},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        cleaned = response.choices[0].message.content.strip()
        if cleaned:
            logging.info("Ollama cleaned: %r → %r", text, cleaned)
            return cleaned
        logging.warning("Ollama returned empty response — using raw transcription.")
        return text

    except Exception as e:
        logging.error("Ollama cleanup failed (%s) — using raw transcription.", e)
        return text
