from pathlib import Path
import tempfile
import unittest
from unittest import mock

import local_transcriber


class Segment:
    def __init__(self, start, text):
        self.start = start
        self.text = text


class FakeModel:
    def transcribe(self, path, **kwargs):
        return iter((Segment(2, "Halo."), Segment(65, "Mari mulai."))), object()


class LocalTranscriberTests(unittest.TestCase):
    def test_local_transcript_has_timestamps(self):
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "rapat.wav"
            audio.write_bytes(b"RIFF")
            with mock.patch.object(
                local_transcriber, "_load_model", return_value=FakeModel()
            ):
                result = local_transcriber.transcribe_audio_local(
                    audio, model_dir=Path(temp) / "models"
                )
        self.assertEqual(result, "[00:00:02] Halo.\n[00:01:05] Mari mulai.")

    def test_rejects_unsupported_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "rapat.txt"
            audio.write_text("bukan audio")
            with self.assertRaises(local_transcriber.LocalTranscriptionError):
                local_transcriber.transcribe_audio_local(
                    audio, model_dir=Path(temp) / "models"
                )


if __name__ == "__main__":
    unittest.main()
