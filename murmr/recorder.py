import numpy as np
import sounddevice as sd
from config import AUDIO_SAMPLERATE

# This list acts as our "tape" — audio chunks get appended here while recording.
_buffer = []
_stream = None


def _on_audio_chunk(indata, frames, time, status):
    """Called automatically by sounddevice every time a new chunk of audio arrives."""
    _buffer.append(indata.copy())


def start_recording():
    """Open the microphone and start collecting audio into the buffer."""
    global _stream, _buffer
    _buffer = []  # Clear any audio from a previous recording
    _stream = sd.InputStream(
        samplerate=AUDIO_SAMPLERATE,
        channels=1,          # Mono — one mic channel is enough for speech
        dtype="float32",     # faster-whisper expects 32-bit floating point numbers
        callback=_on_audio_chunk,
    )
    _stream.start()


def stop_recording() -> np.ndarray:
    """Stop the microphone and return all recorded audio as a single numpy array."""
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None

    if not _buffer:
        return np.zeros(0, dtype="float32")  # Return empty array if nothing was recorded

    # Stitch all the chunks together into one continuous array, then flatten to 1D
    audio = np.concatenate(_buffer, axis=0).flatten()
    return audio
