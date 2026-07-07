import tempfile
from pathlib import Path
import unittest
from unittest import mock

import updater


class VersionTests(unittest.TestCase):
    def test_newer_semantic_version(self):
        self.assertTrue(updater.is_newer_version("v1.2.0", "1.1.9"))
        self.assertFalse(updater.is_newer_version("1.2.0", "1.2.0"))
        self.assertFalse(updater.is_newer_version("continuous", "1.2.0"))


class ReleaseTests(unittest.TestCase):
    release = {
        "tag_name": "v1.1.0",
        "html_url": "https://example.invalid/release",
        "body": "Catatan rilis",
        "assets": [
            {"name": updater.INSTALLER_ASSET, "browser_download_url": "https://x/installer"},
            {"name": updater.CHECKSUM_ASSET, "browser_download_url": "https://x/checksum"},
            {"name": updater.MANIFEST_ASSET, "browser_download_url": "https://x/manifest"},
        ],
    }

    def test_stable_release_is_selected(self):
        with mock.patch.object(
            updater,
            "_request_json",
            side_effect=[self.release, {"version": "1.1.0", "build_id": "abc"}],
        ):
            info = updater.get_update_info("stable", current_version="1.0.0")
        self.assertIsNotNone(info)
        self.assertEqual(info.version, "1.1.0")

    def test_continuous_build_uses_commit_id(self):
        with mock.patch.object(
            updater,
            "_request_json",
            side_effect=[self.release, {"version": "1.0.0", "build_id": "new-sha"}],
        ):
            info = updater.get_update_info("continuous", current_build="old-sha")
        self.assertEqual(info.build_id, "new-sha")

    def test_current_continuous_build_has_no_update(self):
        with mock.patch.object(
            updater,
            "_request_json",
            side_effect=[self.release, {"version": "1.0.0", "build_id": "same-sha"}],
        ):
            info = updater.get_update_info("continuous", current_build="same-sha")
        self.assertIsNone(info)


class DownloadTests(unittest.TestCase):
    def test_checksum_mismatch_is_rejected(self):
        info = updater.UpdateInfo(
            version="1.0.0",
            build_id="abc",
            channel="stable",
            installer_url="https://x/installer",
            checksum_url="https://x/checksum",
            release_url="https://x/release",
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            Path, "home", return_value=Path(tmp)
        ), mock.patch.object(updater, "_download") as download:
            def fake_download(url, destination, limit=updater.MAX_DOWNLOAD_BYTES):
                if "checksum" in url:
                    destination.write_text("0" * 64, encoding="utf-8")
                else:
                    destination.write_bytes(b"not-the-release")

            download.side_effect = fake_download
            with self.assertRaises(updater.UpdateError):
                updater.download_installer(info)


if __name__ == "__main__":
    unittest.main()
