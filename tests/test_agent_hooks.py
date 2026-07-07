import json
import pathlib
import tempfile
import unittest

import agent_hooks


class HookSetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.settings = pathlib.Path(tmp.name) / "settings.json"

    def read(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def test_install_creates_both_events(self):
        agent_hooks.install(self.settings)
        data = self.read()
        for event in agent_hooks.HOOK_EVENTS:
            self.assertEqual(len(data["hooks"][event]), 1)
        self.assertTrue(agent_hooks.is_installed(self.settings))

    def test_install_is_idempotent(self):
        agent_hooks.install(self.settings)
        agent_hooks.install(self.settings)
        data = self.read()
        for event in agent_hooks.HOOK_EVENTS:
            self.assertEqual(len(data["hooks"][event]), 1)

    def test_install_preserves_existing_hooks_and_settings(self):
        self.settings.write_text(
            json.dumps(
                {
                    "model": "opus",
                    "hooks": {
                        "Stop": [
                            {"hooks": [{"type": "command", "command": "echo selesai"}]}
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        agent_hooks.install(self.settings)
        data = self.read()
        self.assertEqual(data["model"], "opus")
        stop_commands = [
            hook["command"]
            for group in data["hooks"]["Stop"]
            for hook in group["hooks"]
        ]
        self.assertIn("echo selesai", stop_commands)
        self.assertEqual(len(data["hooks"]["Stop"]), 2)

    def test_uninstall_removes_only_dogi_entries(self):
        self.settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {"hooks": [{"type": "command", "command": "echo selesai"}]}
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        agent_hooks.install(self.settings)
        agent_hooks.uninstall(self.settings)
        data = self.read()
        self.assertFalse(agent_hooks.is_installed(self.settings))
        self.assertEqual(len(data["hooks"]["Stop"]), 1)
        self.assertNotIn("UserPromptSubmit", data["hooks"])

    def test_uninstall_without_file_is_noop(self):
        agent_hooks.uninstall(self.settings)
        self.assertFalse(self.settings.exists())

    def test_invalid_json_raises_friendly_error(self):
        self.settings.write_text("{rusak", encoding="utf-8")
        with self.assertRaises(agent_hooks.HookError):
            agent_hooks.install(self.settings)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{rusak")
        self.assertFalse(agent_hooks.is_installed(self.settings))

    def test_hook_command_is_recognized_as_dogi(self):
        for status in agent_hooks.HOOK_EVENTS.values():
            command = agent_hooks.hook_command(status)
            self.assertIn(status, command)
            self.assertTrue(agent_hooks._is_dogi_command(command))


if __name__ == "__main__":
    unittest.main()
