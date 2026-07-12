from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from dogi import (
    CANVAS_W,
    DogiApp,
    DesktopPetObject,
    OBJECT_H,
    OBJECT_W,
)
from pet_life import PetLifeStore


def fake_pet(profile_id="dogi-1", x=100, state="idle"):
    pet = SimpleNamespace(
        profile_id=profile_id,
        personality="ceria",
        equipped_accessory="none",
        x=x,
        y=300,
        state=state,
        target_object=None,
        frame_i=0,
        theme="Shiba",
        messages=[],
        center_x=lambda: x + CANVAS_W // 2,
        visual_facing=lambda: 1,
    )

    def set_state(value, duration=None):
        pet.state = value
        pet.state_timer = duration

    pet.set_state = set_state
    pet.show_msg = lambda text, seconds=3: pet.messages.append((text, seconds))
    return pet


class DesktopObjectTests(unittest.TestCase):
    def test_object_drag_is_clamped_across_virtual_desktop(self):
        obj = DesktopPetObject.__new__(DesktopPetObject)
        obj.app = SimpleNamespace(
            screen_left=-1600, screen_top=-200,
            screen_right=1920, screen_bottom=1080,
            screen_w=3520, screen_h=1280,
        )
        obj.win = Mock()

        obj._move_to(-9999, 9999)

        self.assertEqual((obj.x, obj.y), (-1600, 1080 - OBJECT_H))
        obj.win.geometry.assert_called_with(
            f"{OBJECT_W}x{OBJECT_H}-1600+{1080 - OBJECT_H}"
        )

    @patch("dogi.DesktopPetObject")
    def test_toy_drop_assigns_nearest_available_dogi(self, object_type):
        with tempfile.TemporaryDirectory() as root:
            pet = fake_pet()
            app = DogiApp.__new__(DogiApp)
            app.pets = [pet]
            app.desktop_objects = []
            app.home_object = None
            app.pet_life = PetLifeStore(Path(root) / "life.json")
            app.stats = {"kenyang": 80, "energi": 80, "senang": 80}
            app.screen_left = app.screen_top = 0
            app.screen_right, app.screen_bottom = 1920, 1080
            app.screen_w, app.screen_h = 1920, 1080
            app.theme = "Shiba"
            obj = SimpleNamespace(
                kind="bola", category="toy", x=500, y=500, destroy=Mock()
            )
            object_type.return_value = obj

            created = app.spawn_desktop_object("bola")

            self.assertIs(created, obj)
            self.assertIs(pet.target_object, obj)
            self.assertEqual(pet.state, "toy_chase")

    def test_finish_toy_fetch_raises_happiness_and_enters_play(self):
        pet = fake_pet(state="toy_chase")
        obj = SimpleNamespace(kind="frisbee", destroy=Mock())
        pet.target_object = obj
        app = DogiApp.__new__(DogiApp)
        app.pets = [pet]
        app.desktop_objects = [obj]
        app.home_object = None
        app.stats = {"kenyang": 80, "energi": 80, "senang": 60}
        app.capture_album_moment = Mock()

        app.finish_toy_fetch(pet, obj)

        self.assertEqual(pet.state, "toy_play")
        self.assertEqual(app.stats["senang"], 67)
        self.assertNotIn(obj, app.desktop_objects)
        obj.destroy.assert_called_once()

    def test_ball_drop_starts_two_dogi_race_and_loser_recovers(self):
        first = fake_pet("dogi-1", 100)
        second = fake_pet("dogi-2", 300)
        obj = SimpleNamespace(kind="bola", category="toy", x=500, y=500, destroy=Mock())
        app = DogiApp.__new__(DogiApp)
        app.pets = [first, second]
        app.desktop_objects = [obj]
        app.home_object = None
        app.stats = {"kenyang": 80, "energi": 80, "senang": 60}
        app.capture_album_moment = Mock()

        app.on_desktop_object_dropped(obj)

        self.assertIs(first.target_object, obj)
        self.assertIs(second.target_object, obj)
        self.assertEqual((first.state, second.state), ("toy_chase", "toy_chase"))

        app.finish_toy_fetch(first, obj)

        self.assertEqual(first.state, "toy_play")
        self.assertEqual(second.state, "curious")
        self.assertIn(("Hampir dapat!", 2), second.messages)


class TrickAndPersonalityTests(unittest.TestCase):
    def make_app(self, root):
        app = DogiApp.__new__(DogiApp)
        app.pet_life = PetLifeStore(Path(root) / "life.json")
        app.pets = [fake_pet()]
        app.capture_album_moment = Mock()
        return app

    @patch("dogi.random.random", return_value=0.0)
    def test_successful_trick_animates_and_trains(self, _random):
        with tempfile.TemporaryDirectory() as root:
            app = self.make_app(root)

            self.assertTrue(app.perform_trick("putar"))

            self.assertEqual(app.pets[0].state, "spin")
            self.assertEqual(
                app.pet_life.profile("dogi-1")["training"]["putar"], 10
            )
            app.capture_album_moment.assert_called_once()

    def test_personality_changes_spontaneous_weights(self):
        app = DogiApp.__new__(DogiApp)
        app.stats = {"kenyang": 80, "energi": 80, "senang": 80}
        active = fake_pet()
        active.personality = "aktif"
        shy = fake_pet()
        shy.personality = "pemalu"

        active_weights = app.state_weights(active)
        shy_weights = app.state_weights(shy)

        self.assertGreater(active_weights[1], shy_weights[1])
        self.assertGreater(active_weights[7], shy_weights[7])


if __name__ == "__main__":
    unittest.main()
