from array import array
import tempfile
from pathlib import Path
import unittest

from meeting_recorder import MeetingRecorder, pcm16_to_mono_16k


class AudioConversionTests(unittest.TestCase):
    def test_stereo_48k_is_downmixed_to_mono_16k(self):
        stereo = array("h")
        for index in range(4_800):
            stereo.extend((index % 1000, -(index % 1000)))
        result = pcm16_to_mono_16k(stereo.tobytes(), channels=2, source_rate=48_000)
        samples = array("h")
        samples.frombytes(result)
        self.assertEqual(len(samples), 1_600)
        self.assertTrue(all(value == 0 for value in samples))

    def test_native_mono_keeps_pcm_bytes(self):
        original = array("h", (10, -20, 30, -40)).tobytes()
        self.assertEqual(pcm16_to_mono_16k(original, 1, 16_000), original)


class RecorderStateTests(unittest.TestCase):
    def test_stop_is_safe_when_not_recording(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder = MeetingRecorder(Path(temp))
            self.assertFalse(recorder.stop())
            self.assertEqual(recorder.elapsed_seconds, 0)


if __name__ == "__main__":
    unittest.main()
