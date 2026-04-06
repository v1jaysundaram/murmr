"""
murmr — Module Tests
====================
Test individual modules by running:

    python test_modules.py config
    python test_modules.py recorder
    python test_modules.py transcriber

"""

import sys
import os

# Flush print output immediately so messages appear in real time
import functools
print = functools.partial(print, flush=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "murmr"))


def test_config():
    import config
    print("=== config.py ===")
    print(f"  Whisper model:  {config.WHISPER_MODEL}")
    print(f"  Hotkey:         {config.HOTKEY_COMBO}")
    print(f"  Sample rate:    {config.AUDIO_SAMPLERATE} Hz")
    print(f"  Notion token:   {'set' if config.NOTION_TOKEN else 'not set (expected for Phase 1)'}")
    print(f"  Notion page ID: {'set' if config.NOTION_PAGE_ID else 'not set (expected for Phase 1)'}")
    print("  PASS")


def test_recorder():
    import time
    from recorder import start_recording, stop_recording

    print("=== recorder.py ===")
    print("  Recording for 3 seconds... speak now!")
    start_recording()
    time.sleep(3)
    audio = stop_recording()

    expected_samples = 3 * 16000
    print(f"  Samples captured: {len(audio)} (expected ~{expected_samples})")
    print(f"  Audio dtype:      {audio.dtype} (expected float32)")
    print(f"  Peak volume:      {audio.max():.4f} (should be > 0.001 if you spoke)")

    if len(audio) < expected_samples * 0.9:
        print("  WARNING: fewer samples than expected — mic may not be working")
    elif audio.max() < 0.001:
        print("  WARNING: audio is near-silent — check your mic is the default recording device")
    else:
        print("  PASS")


def test_transcriber():
    import time
    from recorder import start_recording, stop_recording
    from transcriber import Transcriber

    print("=== transcriber.py ===")
    print("  Loading Whisper model...")
    t = Transcriber()
    print("  Model loaded.")
    print("  Recording 4 seconds... say something clearly!")
    start_recording()
    time.sleep(4)
    audio = stop_recording()
    print(f"  Peak volume: {audio.max():.4f} (if this is < 0.001, mic isn't picking you up)")
    print("  Transcribing...")
    text = t.transcribe(audio)
    print(f"  Transcribed text: '{text}'")
    if text.strip():
        print("  PASS")
    else:
        print("  WARNING: empty transcription — trying again without VAD filter...")
        from faster_whisper import WhisperModel
        from config import WHISPER_MODEL
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio, language="en", vad_filter=False, beam_size=5)
        text2 = " ".join(s.text.strip() for s in segments)
        print(f"  Without VAD filter: '{text2}'")
        if text2.strip():
            print("  VAD filter is the issue — will fix in transcriber.py")


# ==============================================================================

TESTS = {
    "config": test_config,
    "recorder": test_recorder,
    "transcriber": test_transcriber,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_modules.py <test_name>")
        print(f"Available tests: {', '.join(TESTS)}")
        sys.exit(1)

    name = sys.argv[1]
    if name not in TESTS:
        print(f"Unknown test '{name}'. Available: {', '.join(TESTS)}")
        sys.exit(1)

    TESTS[name]()
