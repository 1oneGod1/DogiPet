from pathlib import Path
import unittest

from PIL import Image

import dogi


ROOT = Path(__file__).resolve().parents[1]


class ReferenceSpriteTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
