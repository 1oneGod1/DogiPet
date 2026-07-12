from pathlib import Path
import unittest

from PIL import Image

import dogi


ROOT = Path(__file__).resolve().parents[1]


class ReferenceSpriteTests(unittest.TestCase):
    def test_walk_cycle_has_four_distinct_leg_poses(self):
        frames = dogi.SPRITE_FRAME_COUNTS["walk"]
        self.assertEqual(frames, 4)
        paths = [
            ROOT / "assets" / "sprites" / "shiba" / f"walk_{index}.png"
            for index in range(frames)
        ]
        images = [Image.open(path).convert("RGBA") for path in paths]
        self.assertEqual(len({image.tobytes() for image in images}), 4)

        # Area kaki harus berubah pada setiap pergantian frame; badan/ekor
        # boleh ikut bob, tetapi langkah tidak boleh hanya berupa torso geser.
        leg_boxes = [image.crop((20, 95, 150, 140)).tobytes()
                     for image in images]
        self.assertEqual(len(set(leg_boxes)), 4)

    def test_right_facing_art_mirrors_only_toward_left_motion(self):
        # Semua sprite digambar menghadap kanan: gerak kanan memakai art asli,
        # gerak kiri dicerminkan. Regresi "jalan kebalik" terjadi saat walk/
        # chase/fetch keliru ditandai sebagai art menghadap kiri.
        for state in ("walk", "chase", "fetch", "idle", "sleep",
                      "meeting_watch"):
            with self.subTest(state=state):
                self.assertFalse(dogi.sprite_is_mirrored(state, 1))
                self.assertTrue(dogi.sprite_is_mirrored(state, -1))

    def test_confused_animation_uses_slow_ping_pong_sequence(self):
        frames = [dogi.sprite_frame_index("think", tick) for tick in range(12)]
        self.assertEqual(frames, [0, 0, 1, 1, 2, 2, 3, 3, 2, 2, 1, 1])

    def test_typing_animation_has_four_heat_levels(self):
        self.assertEqual(dogi.SPRITE_FRAME_COUNTS["type"], 16)
        for heat in range(4):
            with self.subTest(heat=heat):
                frames = [dogi.typing_frame_index(tick, heat)
                          for tick in range(4)]
                self.assertEqual(frames, list(range(heat * 4, heat * 4 + 4)))

    def test_typing_heat_levels_get_progressively_redder(self):
        root = ROOT / "assets" / "sprites" / "coklat"
        blush = (255, 90, 121, 255)
        red_counts = []
        for index in (0, 4, 8, 12):
            image = Image.open(root / f"type_{index}.png").convert("RGBA")
            red_counts.append(sum(
                pixel == blush for pixel in image.get_flattened_data()
            ))
        self.assertEqual(red_counts, sorted(red_counts))
        self.assertEqual(len(set(red_counts)), 4)

    def test_typing_smoke_grows_with_heat_level(self):
        root = ROOT / "assets" / "sprites" / "shiba"
        smoke = (174, 184, 192, 255)
        smoke_counts = []
        for index in (0, 4, 8, 12):
            image = Image.open(root / f"type_{index}.png").convert("RGBA")
            smoke_counts.append(sum(
                pixel == smoke for pixel in image.get_flattened_data()
            ))
        self.assertEqual(smoke_counts, sorted(smoke_counts))
        self.assertEqual(smoke_counts[0], 0)
        self.assertEqual(len(set(smoke_counts)), 4)

    def test_typing_has_complete_standalone_keyboard(self):
        root = ROOT / "assets" / "sprites" / "coklat"
        for index in range(16):
            image = Image.open(root / f"type_{index}.png").convert("RGBA")
            with self.subTest(frame=index):
                # Keyboard mandiri berada di x=15..28, y=24..27.
                self.assertNotEqual(image.getpixel((80, 125))[3], 0)
                self.assertNotEqual(image.getpixel((135, 130))[3], 0)
                self.assertNotEqual(image.getpixel((100, 125))[3], 0)
                self.assertLess(image.getbbox()[2], image.width)

    def test_typing_forelegs_connect_body_to_keyboard(self):
        root = ROOT / "assets" / "sprites" / "shiba"
        for index in range(16):
            image = Image.open(root / f"type_{index}.png").convert("RGBA")
            alpha = image.getchannel("A")
            with self.subTest(frame=index):
                # Kedua koridor kaki depan dari torso (y=18) menuju keyboard
                # (y=24) harus memiliki piksel pada setiap baris logis.
                for logical_y in range(18, 24):
                    row = alpha.crop((75, logical_y * 5, 115,
                                      logical_y * 5 + 5))
                    self.assertIsNotNone(row.getbbox())

    def test_typing_and_scrolling_use_different_props(self):
        root = ROOT / "assets" / "sprites" / "coklat"
        typing = Image.open(root / "type_0.png").convert("RGBA")
        scrolling = Image.open(root / "scroll_down_0.png").convert("RGBA")
        # Area layar tegak hanya boleh muncul pada scrolling; typing memakai
        # keyboard rendah dengan dua telapak aktif.
        screen_box = (105, 70, 155, 120)
        self.assertNotEqual(
            typing.crop(screen_box).tobytes(), scrolling.crop(screen_box).tobytes()
        )

    def test_typing_heat_thresholds_are_gradual(self):
        self.assertEqual(
            [dogi.typing_heat_level(seconds)
             for seconds in (0, 7.9, 8, 19.9, 20, 44.9, 45, 200)],
            [0, 0, 1, 1, 2, 2, 3, 3],
        )

    def test_extra_behaviors_map_to_existing_animation_assets(self):
        self.assertEqual(dogi.sprite_asset_state("curious"), "think")
        self.assertEqual(dogi.sprite_asset_state("tail_wag"), "tail_wag")
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

    def test_pointed_tail_has_a_real_wag_cycle(self):
        root = ROOT / "assets" / "sprites" / "shiba"
        frames = [Image.open(root / f"tail_wag_{index}.png").tobytes()
                  for index in range(4)]
        self.assertGreaterEqual(len(set(frames)), 3)
        self.assertNotEqual(
            Image.open(root / "tail_wag_0.png").tobytes(),
            Image.open(root / "tail_wag_1.png").tobytes(),
        )

    def test_waiting_for_food_is_a_seated_wagging_animation(self):
        root = ROOT / "assets" / "sprites" / "shiba"
        waiting = [Image.open(root / f"wait_food_{index}.png").convert("RGBA")
                   for index in range(4)]
        fetch = Image.open(root / "fetch_0.png").convert("RGBA")

        self.assertEqual(len({frame.tobytes() for frame in waiting}), 4)
        self.assertTrue(all(frame.tobytes() != fetch.tobytes()
                            for frame in waiting))
        # Siluet duduk tetap menyentuh tanah tetapi tidak memakai langkah lebar.
        self.assertTrue(all(frame.getbbox()[3] >= 95 for frame in waiting))


if __name__ == "__main__":
    unittest.main()
