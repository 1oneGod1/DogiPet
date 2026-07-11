from pathlib import Path
import subprocess
import unittest
from unittest import mock

import codex_integration


class CodexIntegrationTests(unittest.TestCase):
    def test_status_reports_authenticated_without_reading_tokens(self):
        executable = Path("C:/tools/codex.exe")
        completed = subprocess.CompletedProcess([], 0, "Logged in using ChatGPT", "")
        with mock.patch.object(
            codex_integration, "find_codex_cli", return_value=executable
        ), mock.patch.object(codex_integration, "_run", return_value=completed) as run:
            status = codex_integration.codex_status()
        self.assertTrue(status.available)
        self.assertTrue(status.authenticated)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[1:], ("login", "status"))

    def test_missing_cli_has_actionable_status(self):
        with mock.patch.object(codex_integration, "find_codex_cli", return_value=None):
            status = codex_integration.codex_status()
        self.assertFalse(status.available)
        self.assertFalse(status.authenticated)
        self.assertIn("BELUM TERPASANG", status.detail)

    def test_minutes_use_ephemeral_read_only_exec_and_stdin(self):
        executable = Path("C:/tools/codex.exe")
        completed = subprocess.CompletedProcess([], 0, "# Notulen\n- Selesai", "")
        with mock.patch.object(codex_integration, "_run", return_value=completed) as run:
            result = codex_integration.create_minutes_with_codex(
                "[00:00] Halo", executable=executable
            )
        self.assertIn("Selesai", result)
        args = run.call_args.args
        kwargs = run.call_args.kwargs
        self.assertIn("exec", args)
        self.assertIn("--ephemeral", args)
        self.assertIn("--ignore-user-config", args)
        self.assertIn("--ignore-rules", args)
        self.assertIn("read-only", args)
        self.assertEqual(kwargs["input"], "[00:00] Halo")
        self.assertTrue(kwargs["capture_output"])


if __name__ == "__main__":
    unittest.main()
