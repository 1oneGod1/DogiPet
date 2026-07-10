"""Jalankan DogiPet otomatis saat Windows login (registry HKCU\\...\\Run).

Registry adalah sumber kebenaran; aplikasi hanya membaca/menulis satu nilai
bernama "DogiPet". Modul hanya memakai standard library agar tetap ringan.
"""

from __future__ import annotations

import pathlib
import sys

try:
    import winreg
    _HAS_REG = True
except ImportError:                       # non-Windows
    winreg = None
    _HAS_REG = False

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DogiPet"


class StartupError(RuntimeError):
    """Kesalahan yang aman ditampilkan kepada pengguna."""


def is_supported() -> bool:
    return _HAS_REG


def launch_command() -> str:
    """Perintah yang dipakai Windows untuk menjalankan DogiPet saat login."""
    executable = pathlib.Path(sys.executable)
    if getattr(sys, "frozen", False):
        return f'"{executable}"'
    # Sumber: pakai pythonw.exe agar tanpa jendela konsol bila tersedia.
    pythonw = executable.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else executable
    script = pathlib.Path(__file__).resolve().parent / "dogi.py"
    return f'"{runner}" "{script}"'


def is_enabled(name: str = APP_NAME) -> bool:
    if not _HAS_REG:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable(name: str = APP_NAME, command: str | None = None) -> None:
    if not _HAS_REG:
        raise StartupError("Jalan-saat-startup hanya tersedia di Windows.")
    command = command or launch_command()
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
    except OSError as exc:
        raise StartupError(f"Gagal menulis pengaturan startup: {exc}") from exc


def disable(name: str = APP_NAME) -> None:
    if not _HAS_REG:
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def set_enabled(enabled: bool, name: str = APP_NAME) -> None:
    if enabled:
        enable(name)
    else:
        disable(name)
