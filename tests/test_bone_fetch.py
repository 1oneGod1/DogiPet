from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from dogi import BONE_H, BONE_W, CANVAS_H, Bone, DogiApp


def make_pet(state="idle", x=100):
    pet = SimpleNamespace(
        state=state,
        x=x,
        y=200,
        fetch_bone=None,
        center_x=lambda: x + 80,
        show_msg=lambda *_args: None,
    )

    def set_state(value):
        pet.state = value

    pet.set_state = set_state
    return pet


class BoneAssignmentTests(unittest.TestCase):
    def make_app(self, pets):
        app = DogiApp.__new__(DogiApp)
        app.pets = pets
        app.bones = []
        app.screen_left = 0
        app.screen_top = 0
        app.screen_right = 1920
        app.screen_bottom = 1080
        app.screen_w = 1920
        app.screen_h = 1080
        app.root = None
        app.transparent_ok = True
        return app

    @patch("dogi.Bone")
    @patch("dogi.random.randint", return_value=900)
    def test_spawn_assigns_bone_and_starts_fetch(self, _randint, bone_type):
        pet = make_pet()
        app = self.make_app([pet])
        bone = SimpleNamespace(x=900, y=300)
        bone_type.return_value = bone

        app.spawn_bone()

        self.assertEqual(app.bones, [bone])
        self.assertIs(pet.fetch_bone, bone)
        self.assertEqual(pet.state, "fetch")
        bone_type.assert_called_once_with(
            app, 900, pet.y + CANVAS_H - BONE_H - 6, pet=pet
        )

    @patch("dogi.Bone")
    def test_clicking_again_does_not_orphan_existing_bone(self, bone_type):
        pet = make_pet(state="fetch")
        existing = SimpleNamespace(x=500, y=300)
        pet.fetch_bone = existing
        app = self.make_app([pet])
        app.bones = [existing]

        app.spawn_bone()

        bone_type.assert_not_called()
        self.assertEqual(app.bones, [existing])
        self.assertIs(pet.fetch_bone, existing)


class DraggableBoneTests(unittest.TestCase):
    def make_bone(self):
        app = SimpleNamespace(
            screen_left=-1920,
            screen_top=-200,
            screen_right=1920,
            screen_bottom=1080,
            screen_w=3840,
            screen_h=1280,
        )
        pet = make_pet(x=200)
        pet.gaze_x = 0
        pet.gaze_y = 0
        bone = Bone.__new__(Bone)
        bone.app = app
        bone.pet = pet
        bone.x = 100
        bone.y = 300
        bone.held = False
        bone._drag_offset = None
        bone.win = Mock()
        pet.fetch_bone = bone
        return bone, pet

    def test_hold_makes_dogi_sit_then_release_resumes_fetch(self):
        bone, pet = self.make_bone()

        bone._on_press(SimpleNamespace(x_root=110, y_root=310))
        self.assertTrue(bone.held)
        self.assertEqual(pet.state, "wait_food")

        bone._on_drag(SimpleNamespace(x_root=-500, y_root=500))
        self.assertEqual((bone.x, bone.y), (-510, 490))
        self.assertEqual((pet.gaze_x, pet.gaze_y), (-500, 500))

        bone._on_release(SimpleNamespace(x_root=-600, y_root=520))
        self.assertFalse(bone.held)
        self.assertIsNone(bone._drag_offset)
        self.assertEqual(pet.state, "fetch")

    def test_drag_is_clamped_to_the_whole_virtual_desktop(self):
        bone, _pet = self.make_bone()

        bone._move_to(-9999, 9999)

        self.assertEqual(bone.x, -1920)
        self.assertEqual(bone.y, 1080 - BONE_H)
        bone.win.geometry.assert_called_with(
            f"{BONE_W}x{BONE_H}-1920+{1080 - BONE_H}"
        )


if __name__ == "__main__":
    unittest.main()
