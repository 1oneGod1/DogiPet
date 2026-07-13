import unittest
from types import SimpleNamespace

from dogi import control_center_summary


class _Store:
    def __init__(self, items):
        self.items = list(items)

    def all(self):
        return list(self.items)


class ControlCenterSummaryTests(unittest.TestCase):
    def make_app(self, **overrides):
        values = {
            "task_store": _Store(
                [SimpleNamespace(done=False), SimpleNamespace(done=True)]
            ),
            "note_store": _Store([object(), object()]),
            "calendar_events": [object()],
            "pets": [object()],
            "codex_authenticated": True,
            "calendar_connected": False,
            "auto_update": True,
            "meeting_recorder": SimpleNamespace(recording=False),
            "voice_recorder": SimpleNamespace(recording=False),
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_summary_counts_local_productivity_data(self):
        summary = control_center_summary(self.make_app())

        self.assertEqual(summary["pending_tasks"], 1)
        self.assertEqual(summary["note_count"], 2)
        self.assertEqual(summary["agenda_count"], 1)
        self.assertEqual(summary["ready_count"], 3)

    def test_recording_and_readiness_are_reported(self):
        app = self.make_app(
            calendar_connected=True,
            voice_recorder=SimpleNamespace(recording=True),
        )

        summary = control_center_summary(app)

        self.assertEqual(summary["ready_count"], 4)
        self.assertTrue(summary["recording"])


if __name__ == "__main__":
    unittest.main()
