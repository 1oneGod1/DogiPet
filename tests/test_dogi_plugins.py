from pathlib import Path
import json
import tempfile
import unittest

from dogi_plugins import PluginManager


class PluginTests(unittest.TestCase):
    def test_only_declarative_allowed_triggers_are_loaded(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "plugin.json").write_text(json.dumps({
                "name": "Tes",
                "python": "import os",
                "triggers": [
                    {"event": "task_done", "message": "Hebat", "state": "happy"},
                    {"event": "run_code", "message": "Tidak boleh"},
                ],
            }), encoding="utf-8")
            manager = PluginManager(folder)
            manager.reload()
            triggers = manager.triggers_for("task_done")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["message"], "Hebat")
        self.assertEqual(manager.triggers_for("run_code"), [])

    def test_template_is_valid_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = PluginManager(temp)
            first = manager.create_template()
            second = manager.create_template()
            self.assertEqual(first, second)
            self.assertGreater(len(manager.plugins), 0)


if __name__ == "__main__":
    unittest.main()
