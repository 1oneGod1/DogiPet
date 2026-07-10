from types import SimpleNamespace
import unittest
from unittest import mock

import dogi
from dogi import (
    CANVAS_H,
    DogiPet,
    ROAM_BOTTOM_MARGIN,
    ROAM_TOP_MARGIN,
    VWALK_SPEED,
    WALK_SPEED,
)


def make_pet():
    pet = DogiPet.__new__(DogiPet)
    pet.app = SimpleNamespace(
        screen_w=1920,
        screen_h=1080,
        agent_thinking=False,
        scroll_reaction_on=True,
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


class VerticalWalkTests(unittest.TestCase):
    def tick_quiet(self, pet):
        """Tick tanpa input: kursor diam di posisi Dogi agar tidak memicu chase."""
        cx, cy = pet.center_x(), pet.y
        pet.app.last_cursor = (cx, cy)
        pet.tick(100.0, cx, cy, False, False, scrolling=0)

    def test_walk_picks_vertical_target_inside_bounds(self):
        pet = make_pet()
        top = ROAM_TOP_MARGIN
        bottom = pet.app.screen_h - CANVAS_H - ROAM_BOTTOM_MARGIN
        for _ in range(25):
            pet.set_state("walk")
            self.assertGreaterEqual(pet.target_y, top)
            self.assertLessEqual(pet.target_y, bottom)

    def test_walk_moves_vertically_and_updates_ground(self):
        pet = make_pet()
        pet.state = "walk"
        pet.target_x = pet.x
        pet.target_y = pet.y + 50
        self.tick_quiet(pet)
        self.assertEqual(pet.y, 500 + VWALK_SPEED)
        self.assertEqual(pet.ground_y, pet.y)
        self.assertEqual(pet.state, "walk")

    def test_walk_finishes_when_both_axes_arrive(self):
        pet = make_pet()
        pet.state = "walk"
        pet.target_x = pet.x + WALK_SPEED
        pet.target_y = pet.y + VWALK_SPEED
        self.tick_quiet(pet)
        self.assertEqual((pet.x, pet.y), (pet.target_x, pet.target_y))
        self.assertEqual(pet.state, "idle")

    def test_chase_follows_cursor_vertically(self):
        pet = make_pet()
        pet.state = "chase"
        pet.state_timer = 99
        cx, cy = pet.center_x(), pet.y - 300
        pet.app.last_cursor = (cx, cy)
        pet.tick(100.0, cx, cy, False, False, scrolling=0)
        self.assertLess(pet.y, 500)
        self.assertEqual(pet.ground_y, pet.y)

    def test_fast_cursor_usually_makes_dogi_glance_without_moving(self):
        pet = make_pet()
        original_position = (pet.x, pet.y)
        cx, cy = pet.center_x() + 120, pet.y + 40
        pet.app.last_cursor = (cx - 100, cy)
        with mock.patch("dogi.random.random", return_value=0.99):
            pet.tick(100.0, cx, cy, False, False, scrolling=0)
        self.assertEqual(pet.state, "glance")
        self.assertEqual((pet.x, pet.y), original_position)
        self.assertEqual((pet.gaze_x, pet.gaze_y), (cx, cy))

    def test_roam_never_leaves_screen(self):
        pet = make_pet()
        pet.state = "walk"
        pet.target_x = pet.x
        pet.target_y = -500
        pet.y = 1
        self.tick_quiet(pet)
        self.assertGreaterEqual(pet.y, 0)

    def test_negative_virtual_desktop_bounds_are_preserved(self):
        pet = make_pet()
        pet.app.screen_left = -1920
        pet.app.screen_top = -200
        pet.app.screen_right = 1920
        pet.app.screen_bottom = 1080
        pet.x = -1919
        pet.y = -199
        pet.state = "walk"
        pet.target_x = -2500
        pet.target_y = -500
        self.tick_quiet(pet)
        self.assertGreaterEqual(pet.x, -1920)
        self.assertGreaterEqual(pet.y, -200)


class MultiMonitorGeometryTests(unittest.TestCase):
    def test_tk_geometry_supports_negative_monitor_coordinates(self):
        self.assertEqual(
            dogi.window_geometry(230, 176, -1720, 120),
            "230x176-1720+120",
        )


if __name__ == "__main__":
    unittest.main()
