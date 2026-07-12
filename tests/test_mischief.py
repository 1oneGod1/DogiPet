from types import SimpleNamespace
import unittest
from unittest import mock

import dogi
from dogi import CANVAS_H, CANVAS_W, DogiApp, DogiPet


def make_pet():
    pet = DogiPet.__new__(DogiPet)
    pet.app = SimpleNamespace(
        screen_w=1920,
        screen_h=1080,
        agent_thinking=False,
        scroll_reaction_on=True,
        sound_style="senyap",   # bikin bark() jadi no-op
        root=None,
        last_key_time=0.0,
        last_cursor=(0, 0),
        on_petted=lambda: None,
    )
    pet.x = 400
    pet.y = 500
    pet.ground_y = 500
    pet.target_x = 400
    pet.target_y = 500
    pet.state = "idle"
    pet.state_timer = 99
    pet.frame_i = 0
    pet.facing = 1
    pet.motion_facing = 1
    pet.blink = False
    pet.temp_msg = None
    pet.fetch_bone = None
    pet.gaze_x = pet.center_x()
    pet.gaze_y = pet.y
    pet.gaze_until = 0.0
    pet.cursor_reaction_until = 0.0
    pet.chase_cooldown_until = 0.0
    pet._drag_start = None
    pet._moved = False
    pet._pre_drag_state = None
    pet.place = lambda: None
    return pet


class SpinTests(unittest.TestCase):
    def test_spin_flips_facing_over_time(self):
        pet = make_pet()
        pet.set_state("spin")
        start = pet.facing
        seen = set()
        for _ in range(6):
            pet.tick(100.0, pet.center_x(), pet.y, False, False, scrolling=0)
            seen.add(pet.facing)
        self.assertEqual(seen, {start, -start})

    def test_spin_ends_in_dizzy_or_happy(self):
        pet = make_pet()
        pet.set_state("spin")
        pet.state_timer = 1
        pet.tick(100.0, pet.center_x(), pet.y, False, False, scrolling=0)
        self.assertIn(pet.state, ("dizzy", "happy"))


class PounceTests(unittest.TestCase):
    def test_pounce_lands_and_shows_message(self):
        pet = make_pet()
        pet.set_state("pounce")
        pet.gaze_x = pet.x + CANVAS_W // 2   # tx == pet.x
        pet.gaze_y = pet.y + CANVAS_H // 2   # ty == pet.y
        pet.tick(100.0, 50, 50, False, False, scrolling=0)
        self.assertEqual(pet.state, "jump")
        self.assertIsNotNone(pet.temp_msg)

    def test_pounce_target_stays_inside_screen(self):
        pet = make_pet()
        pet.set_state("pounce")
        pet.gaze_x = 999999      # jauh di luar layar
        pet.gaze_y = 999999
        for _ in range(60):
            pet.tick(100.0, 50, 50, False, False, scrolling=0)
            self.assertGreaterEqual(pet.x, 0)
            self.assertLessEqual(pet.x, pet.app.screen_w - CANVAS_W)
            self.assertGreaterEqual(pet.y, 0)

    def test_pounce_is_offered_as_a_rare_cursor_reaction(self):
        pet = make_pet()
        pet.state = "idle"
        pet.app.last_cursor = (pet.center_x() - 200, pet.y)
        cx, cy = pet.center_x() + 5, pet.y
        # paksa: bukan chase, tapi lolos undian pounce
        with mock.patch("dogi.random.random", side_effect=[0.99, 0.0]):
            pet.tick(100.0, cx, cy, False, False, scrolling=0)
        self.assertEqual(pet.state, "pounce")
        self.assertEqual((pet.gaze_x, pet.gaze_y), (cx, cy))


class MischiefSchedulerTests(unittest.TestCase):
    def make_app(self, energi=80.0):
        app = DogiApp.__new__(DogiApp)
        app.pets = [make_pet()]
        app.stats = {"kenyang": 80.0, "energi": energi, "senang": 60.0}
        app._mischief_at = 0.0
        app.last_key_time = 0.0
        return app

    def test_mischief_triggers_a_playful_state_and_reschedules(self):
        app = self.make_app()
        with mock.patch("dogi.is_night", return_value=False), \
                mock.patch("dogi.random.random", return_value=0.1):
            app._check_mischief(10_000.0)
        self.assertEqual(app.pets[0].state, "beg")
        self.assertGreater(app._mischief_at, 10_000.0)

    def test_no_mischief_before_scheduled_time(self):
        app = self.make_app()
        app._mischief_at = 20_000.0
        app._check_mischief(10_000.0)
        self.assertEqual(app.pets[0].state, "idle")

    def test_no_mischief_when_dog_is_busy(self):
        app = self.make_app()
        app.pets[0].state = "type"
        with mock.patch("dogi.is_night", return_value=False):
            app._check_mischief(10_000.0)
        self.assertEqual(app.pets[0].state, "type")

    def test_no_mischief_when_tired(self):
        app = self.make_app(energi=5.0)
        with mock.patch("dogi.is_night", return_value=False):
            app._check_mischief(10_000.0)
        self.assertEqual(app.pets[0].state, "idle")


class WeightTests(unittest.TestCase):
    def test_state_weights_matches_choice_list_length(self):
        app = DogiApp.__new__(DogiApp)
        app.stats = {"kenyang": 80.0, "energi": 80.0, "senang": 80.0}
        weights = app.state_weights()
        self.assertEqual(len(weights), 11)
        self.assertTrue(all(w >= 0 for w in weights))


if __name__ == "__main__":
    unittest.main()
