import queue as _queue

import numpy as np
import sounddevice as sd

from config import AUDIO_SAMPLERATE

_buffer      = []
_stream      = None
_current_rms = 0.0   # scaled/smoothed RMS for overlay animation

# ---------------------------------------------------------------------------
# Silence-based segment detection
# Completed sentence segments are placed here for parallel transcription.
# ---------------------------------------------------------------------------
segment_queue    = _queue.Queue()
_silence_samples = 0
_SILENCE_RMS     = 0.015                          # raw RMS below this = silence
_SILENCE_NEEDED  = int(AUDIO_SAMPLERATE * 0.7)   # 0.7s of silence triggers a split
_MIN_SEGMENT     = int(AUDIO_SAMPLERATE * 0.4)   # ignore segments shorter than 0.4s


def get_rms() -> float:
    """Return the smoothed RMS level of the most recent audio chunk (0.0 - 1.0)."""
    return _current_rms


def _flush_segment():
    """Emit the current buffer as a completed segment and reset it."""
    global _buffer, _silence_samples
    total_samples = sum(len(c) for c in _buffer)
    if total_samples < _MIN_SEGMENT:
        return
    audio    = np.concatenate(_buffer, axis=0).flatten()
    _buffer  = []
    _silence_samples = 0
    segment_queue.put(audio)


def _on_audio_chunk(indata, frames, time, status):
    global _current_rms, _silence_samples
    chunk = indata.copy()
    _buffer.append(chunk)

    # Raw RMS for silence detection
    raw_rms = float(np.sqrt(np.mean(chunk ** 2)))

    # Scaled + smoothed RMS for overlay animation
    scaled = min(raw_rms * 8.0, 1.0)
    _current_rms = _current_rms * 0.4 + scaled * 0.6

    # Silence tracking — flush when sustained silence detected
    if raw_rms < _SILENCE_RMS:
        _silence_samples += frames
        if _silence_samples >= _SILENCE_NEEDED:
            _flush_segment()
    else:
        _silence_samples = 0


def start_recording():
    global _stream, _buffer, _current_rms, _silence_samples
    _buffer          = []
    _current_rms     = 0.0
    _silence_samples = 0

    # Drain any stale segments from a previous session
    while not segment_queue.empty():
        try:
            segment_queue.get_nowait()
        except _queue.Empty:
            pass

    _stream = sd.InputStream(
        samplerate=AUDIO_SAMPLERATE,
        channels=1,
        dtype="float32",
        callback=_on_audio_chunk,
    )
    _stream.start()


def stop_recording() -> np.ndarray:
    """Stop the stream and return any remaining buffered audio (the final segment).
    The caller (main.py) is responsible for pushing it to segment_queue."""
    global _stream, _current_rms, _silence_samples
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None
    _current_rms     = 0.0
    _silence_samples = 0

    if not _buffer:
        return np.zeros(0, dtype="float32")

    return np.concatenate(_buffer, axis=0).flatten()
