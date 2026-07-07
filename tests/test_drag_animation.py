from types import SimpleNamespace
import unittest

from dogi import CANVAS_H, CANVAS_W, DogiPet, FRAMES, GRID_H, GRID_W


class FrameTests(unittest.TestCase):
    def test_hold_frames_have_valid_grid_size(self):
        self.assertIn("hold", FRAMES)
        self.assertEqual(len(FRAMES["hold"]), 2)
        for frame in FRAMES["hold"]:
            self.assertEqual(len(frame), GRID_H)
            self.assertTrue(all(len(row) == GRID_W for row in frame))


class DragStateTests(unittest.TestCase):
    def make_pet(self):
        pet = DogiPet.__new__(DogiPet)
        pet.app = SimpleNamespace(
            screen_w=1920,
            screen_h=1080,
            agent_thinking=False,
            on_petted=lambda: None,
        )
        pet.x = 100
        pet.y = 200
        pet.ground_y = 200
        pet.state = "idle"
        pet.state_timer = 10
        pet.frame_i = 0
        pet.fetch_bone = None
        pet._drag_start = None
        pet._moved = False
        pet._pre_drag_state = None
        pet.place = lambda: None
        return pet

    def test_visual_direction_comes_from_actual_motion(self):
        pet = self.make_pet()
        pet.state = "walk"
        pet.facing = -1
        pet.motion_facing = -1
        pet.x = 120
        pet._record_motion_facing(100)
        self.assertEqual(pet.visual_facing(), 1)
        pet.x = 80
        pet._record_motion_facing(100)
        self.assertEqual(pet.visual_facing(), -1)

    def test_typing_timer_does_not_flash_idle_while_still_typing(self):
        pet = self.make_pet()
        pet.app.last_key_time = 0
        pet.app.scroll_reaction_on = True
        pet.app.last_cursor = (pet.center_x(), pet.y)
        pet.state = "type"
        pet.state_timer = 1
        pet.facing = 1
        pet.motion_facing = 1
        pet.blink = False
        pet.tick(100.0, pet.center_x(), pet.y, True, False, scrolling=0)
        self.assertEqual(pet.state, "type")
        self.assertEqual(pet.state_timer, 20)

    def test_drag_enters_hold_and_drop_exits_it(self):
        pet = self.make_pet()
        pet._on_press(SimpleNamespace(x_root=200, y_root=300))
        pet._on_drag(SimpleNamespace(x_root=240, y_root=350))
        self.assertTrue(pet._moved)
        self.assertEqual(pet.state, "hold")
        pet._on_release(SimpleNamespace())
        self.assertEqual(pet.state, "happy")
        self.assertEqual(pet.ground_y, pet.y)
        self.assertIsNone(pet._drag_start)

    def test_drag_position_is_kept_inside_screen(self):
        pet = self.make_pet()
        pet._on_press(SimpleNamespace(x_root=100, y_root=100))
        pet._on_drag(SimpleNamespace(x_root=5000, y_root=5000))
        self.assertEqual(pet.x, pet.app.screen_w - CANVAS_W)
        self.assertEqual(pet.y, pet.app.screen_h - CANVAS_H)


if __name__ == "__main__":
    unittest.main()
