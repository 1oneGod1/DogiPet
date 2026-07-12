"""Opt-in system-audio level meter for Dogi reactions.

Only a rolling RMS number is retained. Audio bytes are never written, queued,
transcribed, or sent anywhere.
"""

from __future__ import annotations

import math
import struct
import threading
import time


def pcm16_rms(data: bytes) -> float:
    if not data or len(data) < 2:
        return 0.0
    count = len(data) // 2
    samples = struct.unpack(f"<{count}h", data[: count * 2])
    return math.sqrt(sum(sample * sample for sample in samples) / count)


class AudioLevelMonitor:
    """Read WASAPI loopback amplitudes without keeping the captured frames."""

    def __init__(self, threshold: float = 9000.0):
        self.threshold = float(threshold)
        self.enabled = False
        self.available = False
        self.last_loud_at = 0.0
        self._thread = None
        self._stop = threading.Event()

    def start(self) -> bool:
        if self.enabled:
            return self.available
        self.enabled = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self.enabled = False
        self._stop.set()

    def loud_recently(self, now: float | None = None, window: float = 1.2) -> bool:
        now = time.time() if now is None else float(now)
        return self.available and now - self.last_loud_at <= window

    def _run(self) -> None:
        interface = None
        stream = None
        try:
            import pyaudiowpatch as pyaudio

            interface = pyaudio.PyAudio()
            device = interface.get_default_wasapi_loopback()
            channels = max(1, int(device.get("maxInputChannels") or 2))
            rate = int(device.get("defaultSampleRate") or 48000)
            stream = interface.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=int(device["index"]),
                frames_per_buffer=1024,
            )
            self.available = True
            while not self._stop.is_set():
                data = stream.read(1024, exception_on_overflow=False)
                if pcm16_rms(data) >= self.threshold:
                    self.last_loud_at = time.time()
        except Exception:
            self.available = False
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if interface is not None:
                try:
                    interface.terminate()
                except Exception:
                    pass
