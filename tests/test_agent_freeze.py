from types import SimpleNamespace
import unittest

import dogi
from dogi import CANVAS_W, DogiApp, DogiPet, THINK_WATCHDOG_S


def make_pet():
    pet = DogiPet.__new__(DogiPet)
    pet.app = SimpleNamespace(
        screen_w=1920,
        screen_h=1080,
        agent_thinking=True,
        scroll_reaction_on=True,
        sound_style="senyap",
        root=None,
        last_key_time=0.0,
        last_cursor=(0, 0),
        remove_bone=lambda bone: None,
        on_fed=lambda: None,
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


class ThinkOverrideTests(unittest.TestCase):
    def test_thinking_engages_when_idle(self):
        pet = make_pet()
        pet.state = "idle"
        pet.tick(100.0, pet.center_x(), pet.y, False, True, scrolling=0)
        self.assertEqual(pet.state, "think")

    def test_fetch_is_not_overridden_by_thinking(self):
        """Regresi: dulu 'think' menimpa fetch tiap tick, jadi tulang percuma."""
        pet = make_pet()
        pet.state = "fetch"
        # tulang jauh supaya belum sampai dalam satu tick
        pet.fetch_bone = SimpleNamespace(x=1200, y=520)
        before = pet.x
        pet.tick(100.0, 50, 50, False, True, scrolling=0)
        self.assertEqual(pet.state, "fetch")
        self.assertNotEqual(pet.x, before)   # benar-benar berjalan mengejar

    def test_eat_is_not_overridden_by_thinking(self):
        pet = make_pet()
        pet.state = "eat"
        pet.state_timer = 5
        pet.tick(100.0, pet.center_x(), pet.y, False, True, scrolling=0)
        self.assertEqual(pet.state, "eat")


class WatchdogTests(unittest.TestCase):
    def make_app(self):
        app = DogiApp.__new__(DogiApp)
        app.agent_thinking = True
        app._thinking_since = 1000.0
        return app

    def test_watchdog_releases_stuck_thinking(self):
        app = self.make_app()
        app._agent_watchdog(1000.0 + THINK_WATCHDOG_S + 1)
        self.assertFalse(app.agent_thinking)

    def test_watchdog_keeps_recent_thinking(self):
        app = self.make_app()
        app._agent_watchdog(1000.0 + 5)
        self.assertTrue(app.agent_thinking)


if __name__ == "__main__":
    unittest.main()
