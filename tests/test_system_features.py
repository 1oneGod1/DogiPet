import unittest

import dogi
import startup


class StartupModuleTests(unittest.TestCase):
    def test_launch_command_is_quoted_and_points_to_app(self):
        command = startup.launch_command()
        self.assertTrue(command.startswith('"'))
        lowered = command.lower()
        self.assertTrue("dogipet" in lowered or "dogi.py" in lowered)

    @unittest.skipUnless(startup.is_supported(), "winreg hanya di Windows")
    def test_enable_disable_round_trip_with_test_key(self):
        name = "DogiPetUnitTest"
        try:
            self.assertFalse(startup.is_enabled(name))
            startup.enable(name, command='"C:\\dummy\\pythonw.exe" "dogi.py"')
            self.assertTrue(startup.is_enabled(name))
        finally:
            startup.disable(name)
        self.assertFalse(startup.is_enabled(name))

    def test_disable_missing_value_is_safe(self):
        # Tidak melempar walau nilai tidak ada.
        startup.disable("DogiPetDefinitelyMissing")


class FullscreenGeometryTests(unittest.TestCase):
    def test_full_cover_is_detected(self):
        monitor = (0, 0, 1920, 1080)
        self.assertTrue(dogi.rect_covers_monitor((0, 0, 1920, 1080), monitor))
        # toleransi kecil di tepi tetap dianggap fullscreen
        self.assertTrue(dogi.rect_covers_monitor((-1, -1, 1921, 1081), monitor))

    def test_maximized_window_leaving_taskbar_is_not_fullscreen(self):
        monitor = (0, 0, 1920, 1080)
        # jendela ter-maximize menyisakan taskbar ~48px di bawah
        self.assertFalse(dogi.rect_covers_monitor((0, 0, 1920, 1032), monitor))

    def test_small_window_is_not_fullscreen(self):
        monitor = (0, 0, 1920, 1080)
        self.assertFalse(dogi.rect_covers_monitor((100, 100, 800, 600), monitor))

    def test_second_monitor_bounds_are_respected(self):
        monitor = (1920, 0, 3840, 1080)
        self.assertTrue(
            dogi.rect_covers_monitor((1920, 0, 3840, 1080), monitor)
        )
        self.assertFalse(
            dogi.rect_covers_monitor((0, 0, 1920, 1080), monitor)
        )


if __name__ == "__main__":
    unittest.main()
