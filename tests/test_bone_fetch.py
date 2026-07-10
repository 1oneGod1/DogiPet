from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dogi import DogiApp


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
        app.screen_right = 1920
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


if __name__ == "__main__":
    unittest.main()
