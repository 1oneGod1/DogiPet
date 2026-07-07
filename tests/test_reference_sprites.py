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
