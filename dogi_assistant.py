"""Penyusunan konteks privat untuk Tanya Dogi.

Modul ini hanya membaca sumber yang dipilih eksplisit pengguna dan membatasi
jumlah data sebelum teks diberikan ke Codex CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


VALID_SOURCES = frozenset({"notes", "tasks", "transcripts", "calendar", "memory"})
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
    memory_count: int = 0
    task_count: int = 0
    truncated: bool = False

    @property
    def source_summary(self) -> str:
        return (
            f"{self.note_count} catatan / {self.transcript_count} transkrip / "
            f"{self.calendar_count} agenda / {self.memory_count} memori / "
            f"{self.task_count} tugas"
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
    memory_store=None,
    task_store=None,
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
    note_count = transcript_count = calendar_count = memory_count = task_count = 0

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

    if "tasks" in selected:
        tasks = list(task_store.all()) if task_store else []
        blocks = [
            f"- [{'x' if item.done else ' '}] {item.title} | prioritas={item.priority} "
            f"| status={item.status} | deadline={item.due_at or 'tidak ada'} "
            f"| detail={_limited(item.details, 1200)}"
            for item in tasks
        ]
        task_count = len(blocks)
        sections.append("# TUGAS LOKAL\n" + ("\n".join(blocks) or "Tidak ada tugas."))

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

    if "memory" in selected:
        memories = list(memory_store.all()) if memory_store else []
        blocks = [
            f"- {_limited(item.label, 160)}: {_limited(item.value, 1200)}"
            for item in memories if item.enabled
        ]
        memory_count = len(blocks)
        sections.append("# MEMORI YANG DIIZINKAN\n" + ("\n".join(blocks) or "Tidak ada memori aktif."))

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
        memory_count,
        task_count,
        truncated,
    )
