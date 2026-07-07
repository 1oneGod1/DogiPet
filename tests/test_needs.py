import pathlib
import tempfile
import unittest
from unittest import mock

import dogi


class StatDecayTests(unittest.TestCase):
    def test_awake_decay_reduces_all_stats(self):
        result = dogi.decay_stats(dict(dogi.DEFAULT_STATS), 60)
        for key in dogi.DEFAULT_STATS:
            self.assertLess(result[key], dogi.DEFAULT_STATS[key])

    def test_sleep_recovers_energy(self):
        stats = {"kenyang": 50.0, "energi": 40.0, "senang": 50.0}
        result = dogi.decay_stats(stats, 30, sleeping=True)
        self.assertGreater(result["energi"], stats["energi"])

    def test_stats_are_clamped(self):
        stats = {"kenyang": 1.0, "energi": 99.0, "senang": 1.0}
        drained = dogi.decay_stats(stats, 100000)
        self.assertEqual(drained["kenyang"], 0)
        recovered = dogi.decay_stats(stats, 100000, sleeping=True)
        self.assertEqual(recovered["energi"], dogi.STAT_MAX)

    def test_zero_minutes_changes_nothing(self):
        stats = {"kenyang": 42.0, "energi": 42.0, "senang": 42.0}
        self.assertEqual(dogi.decay_stats(stats, 0), stats)

    def test_offline_decay_has_floor(self):
        stats = {"kenyang": 90.0, "energi": 90.0, "senang": 90.0}
        result = dogi.offline_decay(stats, 60 * 24 * 7)
        for value in result.values():
            self.assertGreaterEqual(value, dogi.OFFLINE_FLOOR)

    def test_offline_decay_keeps_already_low_values(self):
        stats = {"kenyang": 5.0, "energi": 5.0, "senang": 5.0}
        result = dogi.offline_decay(stats, 600)
        self.assertEqual(result["kenyang"], 5.0)
        self.assertEqual(result["senang"], 5.0)


class ActivityMonitorTests(unittest.TestCase):
    def test_continuous_activity_accumulates(self):
        monitor = dogi.ActivityMonitor(idle_reset_s=300)
        start = 1000.0
        minutes = 0.0
        for step in range(0, 601, 100):  # aktif tiap 100 detik
            minutes = monitor.update(start + step, True)
        self.assertAlmostEqual(minutes, 10.0)

    def test_short_pause_keeps_session(self):
        monitor = dogi.ActivityMonitor(idle_reset_s=300)
        monitor.update(1000.0, True)
        self.assertAlmostEqual(monitor.update(1100.0, False), 100 / 60)
        self.assertAlmostEqual(monitor.update(1200.0, True), 200 / 60)

    def test_long_idle_counts_as_break(self):
        monitor = dogi.ActivityMonitor(idle_reset_s=300)
        monitor.update(1000.0, True)
        self.assertEqual(monitor.update(1400.0, False), 0.0)
        # aktivitas berikutnya memulai sesi baru dari nol
        self.assertEqual(monitor.update(1500.0, True), 0.0)
        self.assertAlmostEqual(monitor.update(1560.0, True), 1.0)


class SoundTests(unittest.TestCase):
    def test_bark_styles_synthesize_wav_files(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            dogi, "CONF_DIR", pathlib.Path(tmp)
        ):
            for style in dogi.BARK_STYLES:
                dogi.ensure_bark_wav(style)
                path = dogi.bark_file(style)
                self.assertTrue(path.exists(), style)
                self.assertEqual(path.read_bytes()[:4], b"RIFF", style)

    def test_senyap_style_has_no_file(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            dogi, "CONF_DIR", pathlib.Path(tmp)
        ):
            dogi.ensure_bark_wav("senyap")
            self.assertFalse(dogi.bark_file("senyap").exists())

    def test_every_sound_choice_is_playable_or_silent(self):
        for style in dogi.SOUND_CHOICES:
            self.assertTrue(style in dogi.BARK_STYLES or style == "senyap")


class TypeFramesTests(unittest.TestCase):
    def test_type_frames_are_valid_grids(self):
        for frame in dogi.FRAMES["type"]:
            self.assertEqual(len(frame), dogi.GRID_H)
            for row in frame:
                self.assertEqual(len(row), dogi.GRID_W)
                for ch in row:
                    self.assertIn(
                        ch, set("konNcpwzrd.")
                    )


class ClockTests(unittest.TestCase):
    def test_night_hours(self):
        self.assertTrue(dogi.is_night(23))
        self.assertTrue(dogi.is_night(2))
        self.assertFalse(dogi.is_night(9))
        self.assertTrue(dogi.is_night(dogi.NIGHT_START_HOUR))
        self.assertFalse(dogi.is_night(dogi.NIGHT_END_HOUR))

    def test_morning_hours(self):
        self.assertTrue(dogi.is_morning(7))
        self.assertFalse(dogi.is_morning(4))
        self.assertFalse(dogi.is_morning(12))


if __name__ == "__main__":
    unittest.main()
