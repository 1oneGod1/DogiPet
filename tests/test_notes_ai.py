import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from notes_ai import (
    AIOrganizerError,
    NotesStore,
    extract_response_text,
    organize_note,
)


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class NotesStoreTests(unittest.TestCase):
    def test_create_update_reload_and_delete(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "notes.json"
            store = NotesStore(path)
            note = store.create("Ide", "teks awal")
            changed = store.update(note.id, "Ide rapi", "- satu")

            reloaded = NotesStore(path).get(note.id)
            self.assertEqual(reloaded.title, "Ide rapi")
            self.assertEqual(reloaded.body, "- satu")
            self.assertNotEqual(changed.updated_at, "")
            self.assertTrue(store.delete(note.id))
            self.assertEqual(store.all(), [])

    def test_notes_are_sorted_by_latest_update(self):
        with TemporaryDirectory() as folder:
            store = NotesStore(Path(folder) / "notes.json")
            first = store.create("Pertama", "1")
            second = store.create("Kedua", "2")
            store.update(first.id, "Pertama", "baru")
            self.assertEqual(store.all()[0].id, first.id)
            self.assertNotEqual(first.id, second.id)


class OpenAINoteTests(unittest.TestCase):
    def test_extracts_all_output_text_blocks(self):
        payload = {
            "output": [
                {"type": "reasoning"},
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "# Judul"},
                        {"type": "output_text", "text": "- Isi"},
                    ],
                },
            ]
        }
        self.assertEqual(extract_response_text(payload), "# Judul\n\n- Isi")

    def test_organizer_sends_private_responses_request(self):
        captured = {}

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeResponse({
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": "# Rapi"}],
                }]
            })

        result = organize_note("catatan acak", "sk-test", opener=opener)
        payload = json.loads(captured["request"].data.decode("utf-8"))
        self.assertEqual(result, "# Rapi")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertEqual(captured["timeout"], 60)

    def test_empty_note_is_rejected_before_network(self):
        with self.assertRaises(AIOrganizerError):
            organize_note("   ", "sk-test", opener=lambda *_a, **_k: None)


if __name__ == "__main__":
    unittest.main()
