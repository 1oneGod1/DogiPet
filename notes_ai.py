"""Catatan lokal dan perapian opsional melalui OpenAI Responses API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import uuid


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_AI_MODEL = "gpt-5.6-luna"
MAX_NOTE_CHARS = 16_000

AI_NOTE_INSTRUCTIONS = """Anda adalah editor catatan berbahasa Indonesia.
Rapikan catatan pengguna menjadi Markdown yang ringkas dan mudah dipindai.
Pertahankan seluruh fakta, nama, angka, tanggal, dan maksud asli. Jangan
menambahkan fakta baru. Gunakan judul singkat, bullet, checklist untuk tugas,
dan bagian 'Tindak lanjut' hanya bila memang ada tindakan. Kembalikan hanya
catatan akhir tanpa komentar pembuka atau penutup."""


class NotesError(RuntimeError):
    pass


class AIOrganizerError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Note:
    id: str
    title: str
    body: str
    created_at: str
    updated_at: str


class NotesStore:
    """Penyimpanan JSON atomik untuk banyak catatan."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _read(self) -> list[Note]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            raw_notes = payload.get("notes", [])
            return [Note(**item) for item in raw_notes if isinstance(item, dict)]
        except Exception as exc:
            raise NotesError("File catatan tidak dapat dibaca.") from exc

    def _write(self, notes: list[Note]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "notes": [asdict(note) for note in notes],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, self.path)

    def all(self) -> list[Note]:
        return sorted(self._read(), key=lambda note: note.updated_at, reverse=True)

    def get(self, note_id: str) -> Note | None:
        return next((note for note in self._read() if note.id == note_id), None)

    def create(self, title: str = "Catatan baru", body: str = "") -> Note:
        timestamp = _now_iso()
        note = Note(
            id=uuid.uuid4().hex,
            title=(title.strip() or "Catatan baru")[:80],
            body=body,
            created_at=timestamp,
            updated_at=timestamp,
        )
        notes = self._read()
        notes.append(note)
        self._write(notes)
        return note

    def update(self, note_id: str, title: str, body: str) -> Note:
        notes = self._read()
        for index, note in enumerate(notes):
            if note.id == note_id:
                changed = Note(
                    id=note.id,
                    title=(title.strip() or "Tanpa judul")[:80],
                    body=body,
                    created_at=note.created_at,
                    updated_at=_now_iso(),
                )
                notes[index] = changed
                self._write(notes)
                return changed
        raise NotesError("Catatan tidak ditemukan.")

    def delete(self, note_id: str) -> bool:
        notes = self._read()
        kept = [note for note in notes if note.id != note_id]
        if len(kept) == len(notes):
            return False
        self._write(kept)
        return True


def extract_response_text(payload: dict) -> str:
    """Gabungkan seluruh blok output_text dari respons HTTP mentah."""
    pieces = []
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    pieces.append(text.strip())
    return "\n\n".join(pieces).strip()


def organize_note(
    note_text: str,
    api_key: str,
    model: str = DEFAULT_AI_MODEL,
    opener=urllib.request.urlopen,
) -> str:
    text = note_text.strip()
    if not text:
        raise AIOrganizerError("Catatan masih kosong.")
    if len(text) > MAX_NOTE_CHARS:
        raise AIOrganizerError(
            f"Catatan terlalu panjang (maksimal {MAX_NOTE_CHARS:,} karakter)."
        )
    if not api_key.strip():
        raise AIOrganizerError("API key OpenAI belum diatur.")

    body = json.dumps(
        {
            "model": model or DEFAULT_AI_MODEL,
            "reasoning": {"effort": "low"},
            "instructions": AI_NOTE_INSTRUCTIONS,
            "input": text,
            "store": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "DogiPet Notes",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            message = detail.get("error", {}).get("message")
        except Exception:
            message = None
        raise AIOrganizerError(message or f"OpenAI menolak permintaan ({exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AIOrganizerError("Tidak dapat terhubung ke OpenAI.") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise AIOrganizerError("Respons OpenAI tidak valid.") from exc

    result = extract_response_text(payload)
    if not result:
        raise AIOrganizerError("OpenAI tidak mengembalikan teks catatan.")
    return result
