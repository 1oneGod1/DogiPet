import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import meeting_ai


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class TranscriptTests(unittest.TestCase):
    def test_formats_speaker_segments_with_timestamps(self):
        result = meeting_ai.format_diarized_transcript({
            "segments": [
                {"speaker": "A", "start": 2, "text": "Halo."},
                {"speaker": "B", "start": 65, "text": "Mari mulai."},
            ]
        })
        self.assertEqual(result, "[00:02] A: Halo.\n[01:05] B: Mari mulai.")

    def test_transcription_uses_diarization_and_auto_chunking(self):
        observed = {}
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "rapat.wav"
            audio.write_bytes(b"RIFF" + b"0" * 100)

            def opener(request, timeout):
                observed["request"] = request
                observed["timeout"] = timeout
                return FakeResponse({
                    "segments": [{"speaker": "A", "start": 0, "text": "Tes"}]
                })

            result = meeting_ai.transcribe_audio(audio, "sk-test", opener=opener)

        request = observed["request"]
        body = request.data
        self.assertEqual(result, "[00:00] A: Tes")
        self.assertIn(b"gpt-4o-transcribe-diarize", body)
        self.assertIn(b'diarized_json', body)
        self.assertIn(b'chunking_strategy', body)
        self.assertIn(b'auto', body)
        self.assertEqual(request.get_header("Authorization"), "Bearer sk-test")

    def test_minutes_request_is_not_stored(self):
        observed = {}

        def opener(request, timeout):
            observed["payload"] = json.loads(request.data)
            return FakeResponse({
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": "# Notulen"}],
                }]
            })

        result = meeting_ai.create_minutes("A: Halo", "sk-test", opener=opener)
        self.assertEqual(result, "# Notulen")
        self.assertFalse(observed["payload"]["store"])

    def test_pipeline_writes_transcript_and_returns_minutes(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            meeting_ai, "transcribe_audio", side_effect=("A: Satu", "B: Dua")
        ), mock.patch.object(
            meeting_ai, "create_minutes", return_value="# Notulen\n- Selesai"
        ):
            paths = [Path(temp) / "a.wav", Path(temp) / "b.wav"]
            for path in paths:
                path.write_bytes(b"RIFF")
            result = meeting_ai.process_meeting(
                paths, "sk-test", Path(temp) / "output"
            )
            self.assertTrue(result.transcript_path.exists())
            self.assertIn("A: Satu", result.transcript)
            self.assertIn("B: Dua", result.transcript)
            self.assertIn("Selesai", result.minutes)


if __name__ == "__main__":
    unittest.main()
