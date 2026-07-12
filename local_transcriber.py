"""Transkripsi rapat lokal dengan faster-whisper (tanpa mengunggah audio)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import threading


DEFAULT_LOCAL_MODEL = "small"
SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}


class LocalTranscriptionError(RuntimeError):
    pass


_MODEL_CACHE = {}
_MODEL_LOCK = threading.Lock()


def local_engine_available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def _timestamp(seconds) -> str:
    value = max(0, int(float(seconds or 0)))
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}"


def _load_model(model_name: str, model_dir: Path):
    if not local_engine_available():
        raise LocalTranscriptionError(
            "Mesin transkripsi lokal belum ikut terpasang. Instal faster-whisper lalu coba lagi."
        )
    try:
        from faster_whisper import WhisperModel
    except (ImportError, OSError) as exc:
        raise LocalTranscriptionError(
            "Komponen transkripsi lokal gagal dimuat. Instal ulang DogiPet."
        ) from exc

    key = (model_name, str(model_dir.resolve()))
    with _MODEL_LOCK:
        model = _MODEL_CACHE.get(key)
        if model is None:
            model_dir.mkdir(parents=True, exist_ok=True)
            try:
                model = WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(model_dir),
                )
            except Exception as exc:
                raise LocalTranscriptionError(
                    "Model Whisper lokal gagal disiapkan. Periksa internet untuk "
                    "unduhan pertama dan ruang disk yang tersedia."
                ) from exc
            _MODEL_CACHE[key] = model
    return model


def transcribe_audio_local(
    audio_path: str | Path,
    *,
    model_name: str = DEFAULT_LOCAL_MODEL,
    model_dir: str | Path,
) -> str:
    path = Path(audio_path)
    if not path.is_file():
        raise LocalTranscriptionError(f"File audio tidak ditemukan: {path.name}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        raise LocalTranscriptionError(f"Format audio tidak didukung: {path.suffix}")

    model = _load_model(model_name, Path(model_dir))
    try:
        segments, _info = model.transcribe(
            str(path),
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=True,
        )
        lines = []
        for segment in segments:
            text = str(segment.text or "").strip()
            if text:
                lines.append(f"[{_timestamp(segment.start)}] {text}")
    except Exception as exc:
        raise LocalTranscriptionError(
            f"Transkripsi lokal gagal untuk {path.name}: {exc}"
        ) from exc
    if not lines:
        raise LocalTranscriptionError(f"Tidak ada ucapan yang dikenali dalam {path.name}.")
    return "\n".join(lines)
