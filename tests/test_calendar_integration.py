from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from calendar_integration import (
    CALENDAR_SCOPE,
    CalendarIntegrationError,
    GoogleCalendarIntegration,
    build_authorization_url,
    load_google_client_config,
    parse_google_event,
    pkce_challenge,
    reminder_due,
)
from dogi import DogiApp


class GoogleOAuthTests(unittest.TestCase):
    def test_desktop_credentials_are_validated(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "credentials.json"
            path.write_text(json.dumps({"installed": {
                "client_id": "client",
                "client_secret": "secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }}), encoding="utf-8")
            self.assertEqual(load_google_client_config(path)["client_id"], "client")

            path.write_text(json.dumps({"web": {}}), encoding="utf-8")
            with self.assertRaises(CalendarIntegrationError):
                load_google_client_config(path)

    def test_authorization_url_uses_readonly_scope_and_pkce(self):
        config = {
            "client_id": "client",
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
        }
        challenge = pkce_challenge("verifier")
        url = build_authorization_url(
            config, "http://127.0.0.1:1234/", "state", challenge
        )
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["scope"], [CALENDAR_SCOPE])
        self.assertEqual(query["code_challenge"], [challenge])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["access_type"], ["offline"])


class _MemoryStore:
    def __init__(self, values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def delete(self, key):
        self.values.pop(key, None)


class _JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class GoogleCalendarClientTests(unittest.TestCase):
    def test_upcoming_uses_primary_calendar_and_bearer_token(self):
        captured = {}
        store = _MemoryStore({
            "google_calendar_client": {"client_id": "client"},
            "google_calendar_token": {
                "access_token": "access",
                "expires_at": datetime.now().timestamp() + 3600,
            },
        })

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _JsonResponse({"items": [{
                "id": "event",
                "summary": "Demo",
                "start": {"dateTime": "2026-07-12T10:00:00+07:00"},
                "end": {"dateTime": "2026-07-12T11:00:00+07:00"},
            }]})

        events = GoogleCalendarIntegration(store, opener=opener).upcoming()

        self.assertEqual([event.title for event in events], ["Demo"])
        self.assertIn("/calendars/primary/events?", captured["request"].full_url)
        self.assertEqual(
            captured["request"].headers["Authorization"], "Bearer access"
        )
        self.assertEqual(captured["timeout"], 45)


class CalendarEventTests(unittest.TestCase):
    def test_timed_event_is_parsed_and_displayed(self):
        event = parse_google_event({
            "id": "abc",
            "summary": "Standup",
            "start": {"dateTime": "2026-07-11T10:00:00+07:00"},
            "end": {"dateTime": "2026-07-11T10:30:00+07:00"},
            "htmlLink": "https://calendar.google.com/event?eid=abc",
        })
        self.assertEqual(event.id, "abc")
        self.assertFalse(event.all_day)
        self.assertIn("Standup", event.display())

    def test_all_day_event_uses_nine_am_for_dogi_reminder(self):
        event = parse_google_event({
            "id": "day",
            "summary": "Libur",
            "start": {"date": "2026-07-12"},
            "end": {"date": "2026-07-13"},
        })
        self.assertTrue(event.all_day)
        self.assertEqual(event.start.hour, 9)

    def test_reminder_only_fires_in_lead_window_once(self):
        now = datetime.now(timezone.utc)
        event = parse_google_event({
            "id": "soon",
            "summary": "Agenda",
            "start": {"dateTime": (now + timedelta(minutes=8)).isoformat()},
            "end": {"dateTime": (now + timedelta(minutes=38)).isoformat()},
        })
        self.assertTrue(reminder_due(event, now, 10, set()))
        self.assertFalse(reminder_due(event, now, 5, set()))
        self.assertFalse(reminder_due(event, now, 10, {"soon"}))

    @patch("dogi.bark")
    def test_dogi_reminds_each_calendar_event_only_once(self, bark_mock):
        now = datetime.now(timezone.utc)
        event = parse_google_event({
            "id": "call",
            "summary": "Review mingguan",
            "start": {"dateTime": (now + timedelta(minutes=5)).isoformat()},
            "end": {"dateTime": (now + timedelta(minutes=35)).isoformat()},
        })
        state = []
        messages = []
        pet = SimpleNamespace(
            set_state=lambda value: state.append(value),
            show_msg=lambda text, duration: messages.append((text, duration)),
        )
        app = DogiApp.__new__(DogiApp)
        app.smoke_test = False
        app.calendar_connected = True
        app._calendar_sync_at = now.timestamp() + 600
        app._calendar_syncing = False
        app.calendar_events = [event]
        app.calendar_reminder_min = 10
        app._calendar_reminded = set()
        app.pets = [pet]
        app.root = None
        app.sound_style = "senyap"

        app._check_calendar(now.timestamp())
        app._check_calendar(now.timestamp() + 1)

        self.assertEqual(state, ["meeting_alert"])
        self.assertEqual(len(messages), 1)
        self.assertIn("Review mingguan", messages[0][0])
        bark_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
