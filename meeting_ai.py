"""Transkripsi audio rapat dan pembuatan notulen melalui OpenAI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import mimetypes
from pathlib import Path
import urllib.error
import urllib.request
import uuid

from notes_ai import DEFAULT_AI_MODEL, extract_response_text


OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-transcribe-diarize"
MAX_AUDIO_BYTES = 24 * 1024 * 1024
SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
MAX_TRANSCRIPT_CHARS = 180_000

MINUTES_INSTRUCTIONS = """Anda adalah sekretaris rapat profesional berbahasa Indonesia.
Buat notulen Markdown hanya dari transkrip yang diberikan. Jangan mengarang.
Gunakan bagian: Ringkasan eksekutif, Topik yang dibahas, Keputusan, Action items
(checkbox, PIC, tenggat bila disebut), Risiko/kendala, dan Pertanyaan terbuka.
Jika informasi tidak ada, tulis 'Tidak disebutkan'. Pertahankan nama, angka,
tanggal, dan label pembicara. Kembalikan hanya notulen akhir."""


class MeetingAIError(RuntimeError):
    pass


@dataclass(frozen=True)
class MeetingAIResult:
    title: str
    minutes: str
    transcript: str
    transcript_path: Path


def _multipart_body(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = f"dogipet-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode("utf-8"),
            b"\r\n",
        ])
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{file_path.name}"\r\n'
        ).encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), boundary


def _openai_error(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        return str(payload.get("error", {}).get("message") or "").strip()
    except Exception:
        return ""


def _clock(seconds) -> str:
    value = max(0, int(float(seconds or 0)))
    return f"{value // 60:02d}:{value % 60:02d}"


def format_diarized_transcript(payload: dict) -> str:
    lines = []
    for segment in payload.get("segments", []):
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        speaker = str(segment.get("speaker") or "Pembicara")
        lines.append(f"[{_clock(segment.get('start'))}] {speaker}: {text}")
    if lines:
        return "\n".join(lines)
    return str(payload.get("text") or "").strip()


def transcribe_audio(
    audio_path: str | Path,
    api_key: str,
    model: str = DEFAULT_TRANSCRIPTION_MODEL,
    opener=urllib.request.urlopen,
) -> str:
    path = Path(audio_path)
    if not path.is_file():
        raise MeetingAIError(f"File audio tidak ditemukan: {path.name}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        raise MeetingAIError(f"Format audio tidak didukung: {path.suffix}")
    if path.stat().st_size > MAX_AUDIO_BYTES:
        raise MeetingAIError(
            f"{path.name} melebihi 24 MB. Pilih potongan audio yang lebih kecil."
        )
    if not api_key.strip():
        raise MeetingAIError("API key OpenAI belum diatur.")

    body, boundary = _multipart_body(
        {
            "model": model,
            "response_format": "diarized_json",
            "chunking_strategy": "auto",
        },
        path,
    )
    request = urllib.request.Request(
        OPENAI_TRANSCRIPTIONS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "DogiPet Meeting Notes",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=300) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _openai_error(exc)
        raise MeetingAIError(detail or f"Transkripsi ditolak OpenAI ({exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise MeetingAIError("Tidak dapat terhubung ke layanan transkripsi OpenAI.") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise MeetingAIError("Respons transkripsi OpenAI tidak valid.") from exc

    transcript = format_diarized_transcript(payload)
    if not transcript:
        raise MeetingAIError(f"Tidak ada ucapan yang dikenali dalam {path.name}.")
    return transcript


def create_minutes(
    transcript: str,
    api_key: str,
    model: str = DEFAULT_AI_MODEL,
    opener=urllib.request.urlopen,
) -> str:
    text = transcript.strip()
    if not text:
        raise MeetingAIError("Transkrip rapat masih kosong.")
    if len(text) > MAX_TRANSCRIPT_CHARS:
        raise MeetingAIError(
            "Transkrip terlalu panjang untuk satu notulen. Proses rekaman dalam beberapa sesi."
        )
    body = json.dumps({
        "model": model or DEFAULT_AI_MODEL,
        "reasoning": {"effort": "low"},
        "instructions": MINUTES_INSTRUCTIONS,
        "input": text,
        "store": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "DogiPet Meeting Notes",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _openai_error(exc)
        raise MeetingAIError(detail or f"Pembuatan notulen ditolak OpenAI ({exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise MeetingAIError("Tidak dapat terhubung ke OpenAI untuk membuat notulen.") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise MeetingAIError("Respons notulen OpenAI tidak valid.") from exc
    result = extract_response_text(payload)
    if not result:
        raise MeetingAIError("OpenAI tidak mengembalikan notulen.")
    return result


def process_meeting(
    audio_paths,
    api_key: str,
    output_dir: str | Path,
    minutes_model: str = DEFAULT_AI_MODEL,
    transcription_model: str = DEFAULT_TRANSCRIPTION_MODEL,
) -> MeetingAIResult:
    paths = [Path(path) for path in audio_paths]
    if not paths:
        raise MeetingAIError("Pilih atau rekam audio rapat lebih dulu.")
    sections = []
    for index, path in enumerate(paths, 1):
        transcript = transcribe_audio(path, api_key, model=transcription_model)
        sections.append(f"## Bagian {index}: {path.name}\n\n{transcript}")
    combined = "\n\n".join(sections)
    minutes = create_minutes(combined, api_key, model=minutes_model)

    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    transcript_path = folder / f"transkrip-{stamp}.txt"
    transcript_path.write_text(combined, encoding="utf-8")
    title = f"Notulen rapat - {datetime.now().strftime('%d %b %Y %H.%M')}"
    return MeetingAIResult(title, minutes, combined, transcript_path)
