from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from dogi_assistant import AssistantContextError, build_assistant_context
from notes_ai import NotesStore


@dataclass
class FakeEvent:
    title: str
    start: datetime
    end: datetime | None = None
    all_day: bool = False

    def local_start(self):
        return self.start.astimezone()


class AssistantContextTests(unittest.TestCase):
    def test_only_selected_sources_are_included(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = NotesStore(root / "notes.json")
            store.create("Rahasia catatan", "Keputusan proyek A")
            transcripts = root / "transcripts"
            transcripts.mkdir()
            (transcripts / "rapat.txt").write_text("Rahasia rapat", encoding="utf-8")
            event = FakeEvent(
                "Rahasia kalender",
                datetime(2026, 7, 12, 9, tzinfo=timezone.utc),
            )
            context = build_assistant_context(
                sources={"notes"},
                note_store=store,
                transcript_dir=transcripts,
                calendar_events=[event],
            )
        self.assertIn("Rahasia catatan", context.text)
        self.assertNotIn("Rahasia rapat", context.text)
        self.assertNotIn("Rahasia kalender", context.text)
        self.assertEqual(context.note_count, 1)

    def test_combines_transcripts_and_calendar_with_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = NotesStore(root / "notes.json")
            transcripts = root / "transcripts"
            transcripts.mkdir()
            (transcripts / "rapat.txt").write_text("Budi mengerjakan UI", encoding="utf-8")
            start = datetime.now(timezone.utc) + timedelta(hours=2)
            event = FakeEvent("Review UI", start, start + timedelta(hours=1))
            context = build_assistant_context(
                sources={"transcripts", "calendar"},
                note_store=store,
                transcript_dir=transcripts,
                calendar_events=[event],
            )
        self.assertIn("Budi mengerjakan UI", context.text)
        self.assertIn("Review UI", context.text)
        self.assertEqual(context.transcript_count, 1)
        self.assertEqual(context.calendar_count, 1)

    def test_requires_explicit_source(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(AssistantContextError):
                build_assistant_context(
                    sources=set(),
                    note_store=NotesStore(Path(temp) / "notes.json"),
                    transcript_dir=Path(temp),
                    calendar_events=[],
                )


if __name__ == "__main__":
    unittest.main()
