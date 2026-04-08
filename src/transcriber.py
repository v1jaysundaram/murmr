import numpy as np
from faster_whisper import WhisperModel
from config import WHISPER_MODEL, AUDIO_SAMPLERATE, WHISPER_LANGUAGE


class Transcriber:
    def __init__(self):
        print(f"[murmr] Loading Whisper model '{WHISPER_MODEL}'...")
        # device="cpu" — runs on your processor, no GPU needed
        # compute_type="int8" — uses less memory with minimal accuracy loss
        self.model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[murmr] Model ready.")

    def transcribe(self, audio: np.ndarray) -> str:
        """Convert a numpy audio array to a text string."""
        if len(audio) == 0:
            return ""

        # faster-whisper returns a generator of Segment objects.
        # Each Segment is a chunk of the audio with its transcribed text.
        # We join them all into one string.
        segments, _ = self.model.transcribe(
            audio,
            language=WHISPER_LANGUAGE or None,  # None = auto-detect; set WHISPER_LANGUAGE in .env
            vad_filter=True,                    # Skip silent parts automatically
            beam_size=5,                        # Higher = more accurate but slower (5 is a good default)
        )

        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()
