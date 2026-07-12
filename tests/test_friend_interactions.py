from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dogi import DogiApp, DogiPet, FRIEND_COOLDOWN, FRIEND_DURATIONS


class FakePet:
    def __init__(self, x, y=400, state="idle"):
        self.x = x
        self.y = y
        self.state = state
        self.state_timer = 10
        self.facing = 1
        self.motion_facing = 1
        self.friend_session = None
        self.friend_role = 0
        self.messages = []

    def center_x(self):
        return self.x + 115

    def set_state(self, state, duration=None):
        self.state = state
        self.state_timer = duration or 10

    def show_msg(self, text, seconds=3):
        self.messages.append((text, seconds))

    def _random_roam_target(self, margin=55):
        return 900, 300


def make_app(*pets):
    app = DogiApp.__new__(DogiApp)
    app.pets = list(pets)
    app._friend_sessions = []
    app._friend_cd = 0
    app.stats = {"kenyang": 80, "energi": 80, "senang": 50}
    return app


def make_live_pet(app, x, y=400):
    pet = DogiPet.__new__(DogiPet)
    pet.app = app
    pet.x = x
    pet.y = y
    pet.ground_y = y
    pet.target_x = x
    pet.target_y = y
    pet.state = "idle"
    pet.state_timer = 20
    pet.frame_i = 0
    pet.facing = 1
    pet.motion_facing = 1
    pet.blink = False
    pet.temp_msg = None
    pet.fetch_bone = None
    pet.friend_session = None
    pet.friend_role = 0
    pet.gaze_x = pet.center_x()
    pet.gaze_y = y
    pet.gaze_until = 0.0
    pet.cursor_reaction_until = 0.0
    pet.chase_cooldown_until = 0.0
    pet.typing_started_at = None
    pet.typing_heat = 0
    pet._drag_start = None
    pet._moved = False
    pet._pre_drag_state = None
    pet.place = lambda: None
    return pet


def make_live_app():
    app = DogiApp.__new__(DogiApp)
    app.screen_left = 0
    app.screen_top = 0
    app.screen_right = 1920
    app.screen_bottom = 1080
    app.screen_w = 1920
    app.screen_h = 1080
    app._friend_sessions = []
    app._friend_cd = 0
    app.stats = {"kenyang": 80, "energi": 80, "senang": 50}
    app.last_key_time = 0.0
    app.last_cursor = (0, 0)
    app.scroll_reaction_on = True
    app.sound_style = "senyap"
    app.root = None
    app.remove_bone = lambda _bone: None
    app.on_fed = lambda: None
    return app


class FriendSessionTests(unittest.TestCase):
    def test_each_interaction_starts_as_one_shared_session(self):
        for mode in FRIEND_DURATIONS:
            with self.subTest(mode=mode):
                a, b = FakePet(100), FakePet(190)
                app = make_app(a, b)
                with patch("dogi.random.choice", return_value=a):
                    started = app._start_friend_session(a, b, mode, 100.0)

                self.assertTrue(started)
                self.assertIs(a.friend_session, b.friend_session)
                self.assertEqual(a.state, f"friend_{mode}")
                self.assertEqual(b.state, f"friend_{mode}")
                self.assertEqual({a.friend_role, b.friend_role}, {-1, 1})
                self.assertEqual(
                    a.friend_session["until"], 100.0 + FRIEND_DURATIONS[mode]
                )

    def test_expired_session_ends_happily_for_both(self):
        a, b = FakePet(100), FakePet(190)
        app = make_app(a, b)
        app._start_friend_session(a, b, "play", 10.0)

        app._update_friend_sessions(10.0 + FRIEND_DURATIONS["play"])

        self.assertEqual(app._friend_sessions, [])
        self.assertIsNone(a.friend_session)
        self.assertIsNone(b.friend_session)
        self.assertEqual((a.state, b.state), ("happy", "happy"))

    def test_interruption_releases_the_other_dogi(self):
        a, b = FakePet(100), FakePet(190)
        app = make_app(a, b)
        app._start_friend_session(a, b, "tussle", 10.0)
        a.set_state("think")

        app._update_friend_sessions(11.0)

        self.assertEqual(a.state, "think")
        self.assertEqual(b.state, "idle")
        self.assertIsNone(a.friend_session)
        self.assertIsNone(b.friend_session)

    @patch("dogi.random.choices", return_value=["tussle"])
    def test_nearby_idle_dogis_can_start_playful_tussle(self, _choices):
        a, b = FakePet(100), FakePet(180)
        app = make_app(a, b)

        app._check_friends(200.0)

        self.assertEqual((a.state, b.state),
                         ("friend_tussle", "friend_tussle"))
        self.assertEqual(app._friend_cd, 200.0 + FRIEND_COOLDOWN)
        self.assertIn("bercanda", a.messages[0][0])

    @patch("dogi.time.time", side_effect=[300.0, 300.0])
    @patch("dogi.random.choices", return_value=["cuddle"])
    def test_menu_action_chooses_nearest_available_friend(
        self, _choices, _time
    ):
        invited = FakePet(100)
        nearest = FakePet(190)
        farther = FakePet(800)
        app = make_app(invited, nearest, farther)

        self.assertTrue(app.start_friend_fun(invited))

        self.assertEqual(invited.state, "friend_cuddle")
        self.assertEqual(nearest.state, "friend_cuddle")
        self.assertEqual(farther.state, "idle")
        self.assertEqual(app._friend_cd, 300.0 + FRIEND_COOLDOWN)

    def test_playing_dogis_approach_and_face_each_other(self):
        app = make_live_app()
        a = make_live_pet(app, 100)
        b = make_live_pet(app, 500)
        app.pets = [a, b]
        app._start_friend_session(a, b, "play", 100.0)
        before = (a.x, b.x)

        a.tick(101.0, 0, 0, False, False)
        b.tick(101.0, 0, 0, False, False)

        self.assertGreater(a.x, before[0])
        self.assertLess(b.x, before[1])
        self.assertEqual((a.facing, b.facing), (1, -1))

    @patch("dogi.random.choice")
    def test_chase_has_a_runner_and_a_moving_chaser(self, choose):
        app = make_live_app()
        runner = make_live_pet(app, 100)
        chaser = make_live_pet(app, 400)
        app.pets = [runner, chaser]
        choose.return_value = runner
        app._start_friend_session(runner, chaser, "chase", 100.0)
        before = (runner.x, chaser.x)

        runner.tick(101.0, 0, 0, False, False)
        chaser.tick(101.0, 0, 0, False, False)

        self.assertNotEqual(runner.x, before[0])
        self.assertNotEqual(chaser.x, before[1])
        self.assertIs(runner.friend_session["runner"], runner)


if __name__ == "__main__":
    unittest.main()
