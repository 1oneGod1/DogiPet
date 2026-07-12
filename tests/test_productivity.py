from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from notes_ai import NotesStore
from productivity import (
    MemoryStore, TaskStore, accessory_unlocked, export_encrypted_backup,
    export_task_ics, global_search, import_encrypted_backup, progression_level,
)


class TaskStoreTests(unittest.TestCase):
    def test_create_update_complete_and_reload(self):
        with tempfile.TemporaryDirectory() as temp:
            store = TaskStore(Path(temp) / "tasks.json")
            task = store.create("Kirim desain", "Ke Budi", priority="high")
            changed = store.update(task.id, due_at="2026-07-13T10:00:00+07:00")
            done, newly_done = store.toggle_done(task.id)
            self.assertTrue(newly_done)
            self.assertTrue(done.done)
            self.assertEqual(changed.priority, "high")
            self.assertEqual(len(store.all()), 1)

    def test_empty_title_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                TaskStore(Path(temp) / "tasks.json").create("  ")

    def test_task_exports_reviewable_calendar_file(self):
        with tempfile.TemporaryDirectory() as temp:
            store = TaskStore(Path(temp) / "tasks.json")
            task = store.create("Review, desain", "Bahas; UI", due_at="2026-07-13T10:00:00+07:00")
            path = export_task_ics(task, Path(temp) / "task.ics")
            content = path.read_text(encoding="utf-8")
            self.assertIn("BEGIN:VEVENT", content)
            self.assertIn("SUMMARY:Review\\, desain", content)
            self.assertIn("DTSTART:20260713T030000Z", content)


class MemoryAndSearchTests(unittest.TestCase):
    def test_memory_requires_explicit_enable_and_can_toggle(self):
        with tempfile.TemporaryDirectory() as temp:
            store = MemoryStore(Path(temp) / "memories.json")
            item = store.create("Jam kerja", "Mulai pukul sembilan")
            self.assertTrue(item.enabled)
            self.assertFalse(store.toggle(item.id).enabled)

    def test_global_search_combines_local_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            notes = NotesStore(root / "notes.json")
            notes.create("Proyek Dogi", "Deadline desain hari Jumat")
            tasks = TaskStore(root / "tasks.json")
            tasks.create("Review desain Dogi")
            results = global_search(
                "desain", notes=notes.all(), tasks=tasks.all(), memories=[],
                transcript_dir=root / "transcripts", calendar_events=[],
            )
            self.assertEqual({item.kind for item in results}, {"catatan", "tugas"})


class ProgressionAndBackupTests(unittest.TestCase):
    def test_accessories_unlock_by_level(self):
        self.assertEqual(progression_level(0), 1)
        self.assertTrue(accessory_unlocked("bandana", 100))
        self.assertFalse(accessory_unlocked("crown", 399))
        self.assertTrue(accessory_unlocked("crown", 400))

    def test_encrypted_backup_round_trip_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "backup.dogibak"
            payload = {"notes": {"notes": [{"title": "Rahasia"}]}}
            export_encrypted_backup(path, payload, "password-kuat")
            self.assertNotIn(b"Rahasia", path.read_bytes())
            self.assertEqual(import_encrypted_backup(path, "password-kuat"), payload)
            with self.assertRaises(ValueError):
                import_encrypted_backup(path, "password-salah")


if __name__ == "__main__":
    unittest.main()
