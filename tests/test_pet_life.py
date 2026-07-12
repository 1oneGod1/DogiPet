from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest

from pet_life import (
    PetLifeStore,
    media_reaction_for,
    mood_for,
    relationship_key,
    seasonal_event,
)
from audio_reactivity import AudioLevelMonitor, pcm16_rms
import struct


class PetLifeStoreTests(unittest.TestCase):
    def make_store(self, root):
        return PetLifeStore(Path(root) / "pet_life.json")

    def test_profiles_relationships_and_personality_persist(self):
        with tempfile.TemporaryDirectory() as root:
            store = self.make_store(root)
            friend = store.add_profile("Husky")
            store.set_personality(friend["id"], "pemalu")
            self.assertEqual(store.relationship("dogi-1", friend["id"]), 20)
            store.adjust_relationship("dogi-1", friend["id"], 15)

            reloaded = self.make_store(root)

            self.assertEqual(len(reloaded.profiles), 2)
            self.assertEqual(reloaded.profile(friend["id"])["personality"], "pemalu")
            self.assertEqual(reloaded.relationship("dogi-1", friend["id"]), 35)

    def test_training_unlocks_rewards_and_caps_at_one_hundred(self):
        with tempfile.TemporaryDirectory() as root:
            store = self.make_store(root)
            for _ in range(8):
                value = store.train("dogi-1", "putar", 15)
            profile = store.profile("dogi-1")
            self.assertEqual(value, 100)
            self.assertIn("glasses", profile["inventory"])
            store.equip("dogi-1", "glasses")
            self.assertEqual(profile["equipped"], "glasses")

    def test_album_is_bounded_and_home_is_saved(self):
        with tempfile.TemporaryDirectory() as root:
            store = self.make_store(root)
            for index in range(205):
                store.add_album_entry("foto", "dogi-1", f"{index}.png")
            store.set_home("kasur", -120, 800)

            self.assertEqual(len(store.data["album"]), 200)
            self.assertEqual(store.data["album"][0]["image_path"], "5.png")
            self.assertEqual(store.data["home"], {"kind": "kasur", "x": -120, "y": 800})

    def test_invalid_file_falls_back_to_safe_default(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "pet_life.json"
            path.write_text("not-json", encoding="utf-8")
            store = PetLifeStore(path)
            self.assertEqual(store.profiles[0]["id"], "dogi-1")

    def test_remove_profile_clears_relationships(self):
        with tempfile.TemporaryDirectory() as root:
            store = self.make_store(root)
            friend = store.add_profile("Golden")
            key = relationship_key("dogi-1", friend["id"])
            self.assertIn(key, store.data["relationships"])
            store.remove_profile(friend["id"])
            self.assertNotIn(key, store.data["relationships"])


class LifeRuleTests(unittest.TestCase):
    def test_moods_prioritize_needs_then_context(self):
        self.assertEqual(mood_for({"kenyang": 10, "energi": 90, "senang": 90}, 12), "LAPAR")
        self.assertEqual(mood_for({"kenyang": 90, "energi": 10, "senang": 90}, 12), "MENGANTUK")
        self.assertEqual(mood_for({"kenyang": 90, "energi": 90, "senang": 10}, 12), "BUTUH TEMAN")
        self.assertEqual(mood_for({"kenyang": 90, "energi": 90, "senang": 90}, 12, "type"), "FOKUS")

    def test_seasonal_events_are_offline_and_deterministic(self):
        self.assertEqual(seasonal_event(datetime(2026, 12, 24))["id"], "salju")
        self.assertEqual(seasonal_event(datetime(2026, 10, 31))["id"], "kostum")
        self.assertEqual(seasonal_event(datetime(2026, 4, 2))["id"], "bunga")

    def test_media_detection_uses_title_only(self):
        self.assertEqual(media_reaction_for("Spotify - Daily Mix"), "dance")
        self.assertEqual(media_reaction_for("Lo-fi relaxing music - YouTube Music"), "calm")
        self.assertIsNone(media_reaction_for("Visual Studio Code"))

    def test_audio_meter_keeps_only_amplitude_and_recent_timestamp(self):
        quiet = struct.pack("<4h", 0, 0, 0, 0)
        loud = struct.pack("<4h", 12000, -12000, 12000, -12000)
        self.assertEqual(pcm16_rms(quiet), 0)
        self.assertGreater(pcm16_rms(loud), 10000)
        monitor = AudioLevelMonitor()
        monitor.available = True
        monitor.last_loud_at = 100.0
        self.assertTrue(monitor.loud_recently(100.5))
        self.assertFalse(monitor.loud_recently(103.0))


if __name__ == "__main__":
    unittest.main()
