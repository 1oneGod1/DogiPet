"""Perekaman rapat lokal melalui mikrofon atau WASAPI speaker loopback."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import threading
import time
import wave

try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO_CAPTURE = True
except ImportError:  # source checkout sebelum requirements dipasang
    pyaudio = None
    HAS_AUDIO_CAPTURE = False


TARGET_RATE = 16_000
SEGMENT_SECONDS = 9 * 60
SEGMENT_FRAMES = TARGET_RATE * SEGMENT_SECONDS
FRAMES_PER_BUFFER = 2_048


class MeetingRecorderError(RuntimeError):
    pass


@dataclass(frozen=True)
class RecordingResult:
    folder: Path
    files: tuple[Path, ...]
    duration_seconds: float
    source: str
    device_name: str


def pcm16_to_mono_16k(data: bytes, channels: int, source_rate: int) -> bytes:
    """Downmix dan resample PCM16 ke mono 16 kHz untuk transkripsi ucapan."""
    channels = max(1, int(channels))
    source_rate = max(1, int(source_rate))
    samples = array("h")
    samples.frombytes(data)
    frame_count = len(samples) // channels
    if frame_count <= 0:
        return b""

    if channels == 1:
        mono = samples
    else:
        mono = array("h")
        for offset in range(0, frame_count * channels, channels):
            value = sum(samples[offset:offset + channels]) / channels
            mono.append(max(-32768, min(32767, round(value))))

    if source_rate == TARGET_RATE:
        return mono.tobytes()

    output_count = max(1, round(frame_count * TARGET_RATE / source_rate))
    output = array("h")
    last_index = frame_count - 1
    for output_index in range(output_count):
        source_position = output_index * source_rate / TARGET_RATE
        left = min(last_index, int(source_position))
        right = min(last_index, left + 1)
        fraction = source_position - left
        value = mono[left] + (mono[right] - mono[left]) * fraction
        output.append(max(-32768, min(32767, round(value))))
    return output.tobytes()


class MeetingRecorder:
    """Perekam thread-safe; event hasil dipoll oleh loop Tkinter."""

    def __init__(self, recordings_dir: str | Path):
        self.recordings_dir = Path(recordings_dir)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=256)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.recording = False
        self.started_at = 0.0
        self.source = "system"

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, time.time() - self.started_at) if self.recording else 0.0

    def start(self, source: str = "system") -> bool:
        if self.recording:
            return False
        if not HAS_AUDIO_CAPTURE:
            raise MeetingRecorderError(
                "Backend audio belum terpasang. Instal requirements.txt lalu coba lagi."
            )
        self.source = "microphone" if source == "microphone" else "system"
        self._stop.clear()
        self._audio_queue = queue.Queue(maxsize=256)
        self.started_at = time.time()
        self.recording = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="dogipet-meeting-recorder"
        )
        self._thread.start()
        return True

    def stop(self) -> bool:
        if not self.recording:
            return False
        self._stop.set()
        return True

    def close(self, timeout: float = 3.0) -> None:
        self.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def poll(self) -> list[tuple[str, object]]:
        result = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except queue.Empty:
                return result

    def _device(self, manager):
        if self.source == "microphone":
            return manager.get_default_input_device_info()
        try:
            return manager.get_default_wasapi_loopback()
        except OSError as exc:
            raise MeetingRecorderError(
                "Speaker loopback WASAPI tidak ditemukan. Pilih Mikrofon atau periksa output Windows."
            ) from exc

    def _open_stream(self, manager, device, callback):
        device_index = int(device["index"])
        if self.source == "microphone":
            # Format ringan lebih dulu; beberapa driver lama hanya menerima
            # format native sehingga fallback tetap disediakan.
            try:
                return manager.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=TARGET_RATE,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=FRAMES_PER_BUFFER,
                    stream_callback=callback,
                    start=False,
                ), 1, TARGET_RATE
            except OSError:
                pass
        channels = max(1, int(device.get("maxInputChannels") or 1))
        rate = max(8_000, int(device.get("defaultSampleRate") or 48_000))
        return manager.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=FRAMES_PER_BUFFER,
            stream_callback=callback,
            start=False,
        ), channels, rate

    def _run(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder = self.recordings_dir / f"rapat-{timestamp}"
        folder.mkdir(parents=True, exist_ok=True)
        files: list[Path] = []
        writer = None
        segment_frames = 0
        total_frames = 0
        dropped_chunks = 0
        device_name = ""
        failed = False

        def callback(in_data, _frame_count, _time_info, _status):
            nonlocal dropped_chunks
            try:
                self._audio_queue.put_nowait(in_data)
            except queue.Full:
                dropped_chunks += 1
            return (None, pyaudio.paContinue)

        def open_segment():
            path = folder / f"bagian-{len(files) + 1:03d}.wav"
            handle = wave.open(str(path), "wb")
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(TARGET_RATE)
            files.append(path)
            return handle

        try:
            with pyaudio.PyAudio() as manager:
                device = self._device(manager)
                device_name = str(device.get("name") or "Perangkat audio")
                stream, channels, source_rate = self._open_stream(
                    manager, device, callback
                )
                with stream:
                    stream.start_stream()
                    self.events.put(("started", device_name))
                    while not self._stop.is_set() or not self._audio_queue.empty():
                        try:
                            raw = self._audio_queue.get(timeout=0.12)
                        except queue.Empty:
                            continue
                        pcm = pcm16_to_mono_16k(raw, channels, source_rate)
                        if not pcm:
                            continue
                        frames = len(pcm) // 2
                        if writer is None:
                            writer = open_segment()
                        writer.writeframesraw(pcm)
                        segment_frames += frames
                        total_frames += frames
                        if segment_frames >= SEGMENT_FRAMES:
                            writer.close()
                            writer = None
                            segment_frames = 0
                    if stream.is_active():
                        stream.stop_stream()
        except Exception as exc:
            failed = True
            message = str(exc).strip() or exc.__class__.__name__
            self.events.put(("error", f"Perekaman gagal: {message}"))
        finally:
            if writer is not None:
                writer.close()
            self.recording = False
            self.started_at = 0.0

        files = [path for path in files if path.exists() and path.stat().st_size > 44]
        if failed:
            return
        if not files:
            try:
                folder.rmdir()
            except OSError:
                pass
            self.events.put(("error", "Tidak ada audio yang terekam."))
            return

        duration = total_frames / TARGET_RATE
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": self.source,
            "device": device_name,
            "duration_seconds": round(duration, 2),
            "segments": [path.name for path in files],
            "dropped_chunks": dropped_chunks,
        }
        (folder / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.events.put((
            "stopped",
            RecordingResult(
                folder=folder,
                files=tuple(files),
                duration_seconds=duration,
                source=self.source,
                device_name=device_name,
            ),
        ))
