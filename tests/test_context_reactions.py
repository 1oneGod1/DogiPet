from types import SimpleNamespace
import unittest
from unittest import mock

import dogi


class MeetingMatcherTests(unittest.TestCase):
    def test_supported_native_meeting_windows(self):
        cases = (
            ("Zoom.exe", "Zoom Meeting"),
            ("ms-teams.exe", "Project sync | Microsoft Teams Meeting"),
            ("Webex.exe", "Weekly Webex Meeting"),
            ("Slack.exe", "Design team - Slack Huddle"),
            ("Discord.exe", "Friends - Discord Call"),
        )
        for executable, title in cases:
            with self.subTest(executable=executable, title=title):
                self.assertTrue(dogi.is_meeting_window(executable, title))

    def test_supported_browser_meeting_windows(self):
        self.assertTrue(
            dogi.is_meeting_window(
                "chrome.exe", "Meet - abc-defg-hij - Google Chrome"
            )
        )
        self.assertTrue(
            dogi.is_meeting_window("msedge.exe", "Client call - Google Meet")
        )

    def test_normal_app_windows_are_not_meetings(self):
        cases = (
            ("chrome.exe", "YouTube - Google Chrome"),
            ("ms-teams.exe", "Chat | Microsoft Teams"),
            ("Zoom.exe", "Zoom Workplace"),
            ("Slack.exe", "general - Slack"),
            ("explorer.exe", "Google Meet notes"),
        )
        for executable, title in cases:
            with self.subTest(executable=executable, title=title):
                self.assertFalse(dogi.is_meeting_window(executable, title))


class ContextFrameTests(unittest.TestCase):
    def test_context_animation_frames_have_valid_grid_size(self):
        for state in (
            "scroll_up",
            "scroll_down",
            "meeting_alert",
            "meeting_watch",
        ):
            with self.subTest(state=state):
                self.assertEqual(len(dogi.FRAMES[state]), 2)
                for frame in dogi.FRAMES[state]:
                    self.assertEqual(len(frame), dogi.GRID_H)
                    self.assertTrue(
                        all(len(row) == dogi.GRID_W for row in frame)
                    )

    def test_scroll_callback_tracks_direction(self):
        app = dogi.DogiApp.__new__(dogi.DogiApp)
        app.last_scroll_time = 0
        app.scroll_direction = 0
        app._on_scroll(0, 0, 0, 1)
        self.assertEqual(app.scroll_direction, 1)
        self.assertGreater(app.last_scroll_time, 0)
        app._on_scroll(0, 0, 0, -1)
        self.assertEqual(app.scroll_direction, -1)


class MeetingReactionTests(unittest.TestCase):
    def test_new_meeting_faces_window_and_enters_alert(self):
        state = {"value": "idle", "message": ""}
        pet = SimpleNamespace(
            x=100,
            facing=-1,
            state="idle",
            _drag_start=None,
            _moved=False,
            center_x=lambda: 200,
            set_state=lambda value: state.update(value=value),
            show_msg=lambda value, _seconds: state.update(message=value),
        )
        app = dogi.DogiApp.__new__(dogi.DogiApp)
        app.smoke_test = False
        app.meeting_reaction_on = True
        app.meeting_bark_on = False
        app.meeting_active = False
        app.meeting_title = ""
        app._meeting_key = None
        app._meeting_poll_at = 0.0
        app._meeting_last_seen = 0.0
        app._meeting_watch_at = 0.0
        app.pets = [pet]

        candidate = {
            "hwnd": 123,
            "title": "Zoom Meeting",
            "executable": "Zoom.exe",
            "center_x": 1400,
            "area": 900_000,
        }
        with mock.patch.object(
            dogi, "visible_meeting_windows", return_value=[candidate]
        ):
            app._check_meeting(100.0)

        self.assertTrue(app.meeting_active)
        self.assertEqual(app.meeting_title, "Zoom")
        self.assertEqual(pet.facing, 1)
        self.assertEqual(state["value"], "meeting_alert")
        self.assertTrue(state["message"])


if __name__ == "__main__":
    unittest.main()
