"""Penyusunan konteks privat untuk Tanya Dogi.

Modul ini hanya membaca sumber yang dipilih eksplisit pengguna dan membatasi
jumlah data sebelum teks diberikan ke Codex CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


VALID_SOURCES = frozenset({"notes", "transcripts", "calendar"})
MAX_CONTEXT_CHARS = 110_000
MAX_NOTES = 30
MAX_TRANSCRIPTS = 12
MAX_ITEM_CHARS = 12_000


class AssistantContextError(RuntimeError):
    pass


@dataclass(frozen=True)
class AssistantContext:
    text: str
    note_count: int
    transcript_count: int
    calendar_count: int
    truncated: bool = False

    @property
    def source_summary(self) -> str:
        return (
            f"{self.note_count} catatan / {self.transcript_count} transkrip / "
            f"{self.calendar_count} agenda"
        )


def _limited(text: str, limit: int = MAX_ITEM_CHARS) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n[…dipotong oleh DogiPet…]"


def build_assistant_context(
    *,
    sources,
    note_store,
    transcript_dir: str | Path,
    calendar_events,
    now: datetime | None = None,
) -> AssistantContext:
    selected = set(sources or ()) & VALID_SOURCES
    if not selected:
        raise AssistantContextError("Pilih minimal satu sumber untuk Tanya Dogi.")

    current = (now or datetime.now().astimezone()).astimezone()
    sections = [
        "# KONTEKS DOGIPET",
        f"Waktu lokal saat ini: {current.strftime('%A, %d %B %Y %H:%M %Z')}",
    ]
    note_count = transcript_count = calendar_count = 0

    if "notes" in selected:
        notes = list(note_store.all())[:MAX_NOTES]
        note_count = len(notes)
        blocks = []
        for note in notes:
            blocks.append(
                f"## Catatan: {_limited(note.title, 160)}\n"
                f"Diperbarui: {note.updated_at}\n{_limited(note.body)}"
            )
        sections.append("# CATATAN LOKAL\n" + ("\n\n".join(blocks) or "Tidak ada catatan."))

    if "transcripts" in selected:
        folder = Path(transcript_dir)
        paths = []
        if folder.is_dir():
            paths = sorted(
                (path for path in folder.glob("*.txt") if path.is_file()),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )[:MAX_TRANSCRIPTS]
        blocks = []
        for path in paths:
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            transcript_count += 1
            blocks.append(f"## Transkrip: {path.name}\n{_limited(content)}")
        sections.append(
            "# TRANSKRIP RAPAT\n" + ("\n\n".join(blocks) or "Tidak ada transkrip.")
        )

    if "calendar" in selected:
        blocks = []
        for event in tuple(calendar_events or ()):
            start = event.local_start()
            end = event.end.astimezone() if event.end else None
            when = start.strftime("%A, %d %B %Y %H:%M")
            if event.all_day:
                when = start.strftime("%A, %d %B %Y (seharian)")
            elif end:
                when += f"–{end.strftime('%H:%M')}"
            blocks.append(f"- {when} — {_limited(event.title, 240)}")
        calendar_count = len(blocks)
        sections.append("# AGENDA KALENDER\n" + ("\n".join(blocks) or "Tidak ada agenda."))

    combined = "\n\n".join(sections)
    truncated = len(combined) > MAX_CONTEXT_CHARS
    if truncated:
        combined = combined[:MAX_CONTEXT_CHARS].rstrip() + (
            "\n\n[…konteks dipotong karena batas privasi/ukuran DogiPet…]"
        )
    return AssistantContext(
        combined,
        note_count,
        transcript_count,
        calendar_count,
        truncated,
    )
