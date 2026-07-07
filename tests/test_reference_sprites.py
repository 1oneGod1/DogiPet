from pathlib import Path
import unittest

from PIL import Image

import dogi


ROOT = Path(__file__).resolve().parents[1]


class ReferenceSpriteTests(unittest.TestCase):
    def test_left_native_running_art_is_mirrored_toward_motion(self):
        for state in ("walk", "chase", "fetch"):
            with self.subTest(state=state):
                self.assertTrue(dogi.sprite_is_mirrored(state, 1))
                self.assertFalse(dogi.sprite_is_mirrored(state, -1))
        self.assertFalse(dogi.sprite_is_mirrored("idle", 1))
        self.assertTrue(dogi.sprite_is_mirrored("idle", -1))

    def test_confused_animation_uses_slow_ping_pong_sequence(self):
        frames = [dogi.sprite_frame_index("think", tick) for tick in range(12)]
        self.assertEqual(frames, [0, 0, 1, 1, 2, 2, 3, 3, 2, 2, 1, 1])

    def test_typing_animation_uses_eight_frame_strip(self):
        frames = [dogi.sprite_frame_index("type", tick) for tick in range(8)]
        self.assertEqual(frames, list(range(8)))

    def test_typing_loop_closes_on_the_same_pose(self):
        root = ROOT / "assets" / "sprites" / "coklat"
        self.assertEqual(
            Image.open(root / "type_0.png").tobytes(),
            Image.open(root / "type_7.png").tobytes(),
        )

    def test_typing_laptop_has_complete_screen_and_keyboard_base(self):
        root = ROOT / "assets" / "sprites" / "coklat"
        for index in range(8):
            image = Image.open(root / f"type_{index}.png").convert("RGBA")
            with self.subTest(frame=index):
                # Logical laptop base is x=21..29, y=25..27 at SCALE=5.
                self.assertNotEqual(image.getpixel((110, 130))[3], 0)
                self.assertNotEqual(image.getpixel((145, 135))[3], 0)
                self.assertNotEqual(image.getpixel((135, 110))[3], 0)
                self.assertLess(image.getbbox()[2], image.width)

    def test_extra_behaviors_map_to_existing_animation_assets(self):
        self.assertEqual(dogi.sprite_asset_state("curious"), "think")
        self.assertEqual(dogi.sprite_asset_state("tail_wag"), "dig")
        self.assertEqual(dogi.sprite_asset_state("beg"), "happy")
        self.assertEqual(dogi.sprite_asset_state("zoomies"), "chase")

    def test_every_theme_and_state_has_all_directional_frames(self):
        for theme in dogi.COLOR_THEMES:
            theme_dir = ROOT / "assets" / "sprites" / theme.lower()
            for state, count in dogi.SPRITE_FRAME_COUNTS.items():
                for index in range(count):
                    for suffix in ("", "_left"):
                        path = theme_dir / f"{state}_{index}{suffix}.png"
                        with self.subTest(theme=theme, state=state, frame=index, suffix=suffix):
                            self.assertTrue(path.exists())

    def test_sprite_frames_are_transparent_and_share_canvas_size(self):
        sample_dir = ROOT / "assets" / "sprites" / "coklat"
        for state, count in dogi.SPRITE_FRAME_COUNTS.items():
            for index in range(count):
                path = sample_dir / f"{state}_{index}.png"
                image = Image.open(path)
                with self.subTest(state=state, frame=index):
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.size, (dogi.SPR_W, dogi.SPR_H))
                    self.assertEqual(image.getchannel("A").getextrema()[0], 0)
                    self.assertIsNotNone(image.getbbox())

    def test_every_sprite_uses_original_five_pixel_blocks(self):
        sample_dir = ROOT / "assets" / "sprites" / "coklat"
        for path in sample_dir.glob("*.png"):
            image = Image.open(path).convert("RGBA")
            for y in range(0, image.height, dogi.SCALE):
                for x in range(0, image.width, dogi.SCALE):
                    block = image.crop(
                        (x, y, x + dogi.SCALE, y + dogi.SCALE)
                    )
                    colors = set(block.get_flattened_data())
                    with self.subTest(sprite=path.name, x=x, y=y):
                        self.assertEqual(len(colors), 1)


if __name__ == "__main__":
    unittest.main()
