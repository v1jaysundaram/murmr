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

SYSTEM_PROMPT = """\
You are a transcription cleanup assistant for a voice dictation app.

Your job is to clean up raw speech-to-text output. Follow these rules strictly:

1. REMOVE filler words and sounds: um, uh, ah, er, hmm, like (when used as filler), \
you know, basically, literally (when used as filler), right (when used as filler), \
so (when used only as a sentence opener with no meaning), kind of, sort of.

2. HANDLE self-corrections: when the speaker corrects themselves mid-sentence, \
keep only the final intended version and drop the false start and the correction \
marker (e.g. "sorry", "wait", "no", "I mean", "actually", "scratch that").
   Examples:
   - "Send it to Mark, sorry, John" → "Send it to John"
   - "Let's meet on Monday, wait no, Tuesday" → "Let's meet on Tuesday"
   - "I think we should, actually we need to cancel" → "We need to cancel"
   - "Call the, um, the client" → "Call the client"

3. FIX grammar errors that are artifacts of speech recognition — run-on words, \
missing capitalization at the start, obvious mishears (e.g. "their" vs "there" \
when context is clear). Do NOT fix intentional informal grammar (contractions, \
casual phrasing) — preserve the speaker's voice.

4. DO NOT paraphrase, summarize, or change the meaning. Keep the same words \
where possible. Do not add information that wasn't in the original.

5. Return ONLY the cleaned text. No explanations, no quotes around the output, \
no commentary.

If the input is already clean, return it unchanged."""


def clean_transcription(text: str, api_key: str, model: str = "gpt-4o-mini") -> str:
    """
    Clean up a raw Whisper transcription using OpenAI.

    Returns the cleaned text, or the original text if the API call fails.
    Never raises — failures are logged and the raw transcription is preserved.
    """
    if not text.strip():
        return text

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": text},
            ],
            max_tokens=500,
            temperature=0.1,
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
        import openai
        client = openai.OpenAI(api_key="ollama", base_url=endpoint)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": text},
            ],
            max_tokens=500,
            temperature=0.1,
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
