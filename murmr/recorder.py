import numpy as np
import sounddevice as sd
from config import AUDIO_SAMPLERATE

_buffer = []
_stream = None
_current_rms = 0.0   # live RMS level, read by the overlay animation


def get_rms() -> float:
    """Return the smoothed RMS level of the most recent audio chunk (0.0 - 1.0)."""
    return _current_rms


def _on_audio_chunk(indata, frames, time, status):
    global _current_rms
    _buffer.append(indata.copy())
    # RMS of this chunk, clamped to 0–1 and lightly smoothed
    rms = float(np.sqrt(np.mean(indata ** 2)))
    rms = min(rms * 8.0, 1.0)           # scale up (speech ~0.05–0.15 raw → 0.4–1.0)
    _current_rms = _current_rms * 0.4 + rms * 0.6   # low-pass smooth


def start_recording():
    global _stream, _buffer, _current_rms
    _buffer = []
    _current_rms = 0.0
    _stream = sd.InputStream(
        samplerate=AUDIO_SAMPLERATE,
        channels=1,
        dtype="float32",
        callback=_on_audio_chunk,
    )
    _stream.start()


def stop_recording() -> np.ndarray:
    global _stream, _current_rms
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None
    _current_rms = 0.0

    if not _buffer:
        return np.zeros(0, dtype="float32")

    return np.concatenate(_buffer, axis=0).flatten()
