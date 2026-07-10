"""
Dogi v3 — Pixel dog yang hidup di desktopmu (versi lengkap!)

Cara pakai:
    python dogi.py

Fitur lengkap:
    - Jalan-jalan, tidur, mengejar kursor cepat, mata mengikuti kursor
    - MENGGALI dengan semangat saat kamu mengetik (butuh: pip install pynput)
    - BERI TULANG: Dogi lari mengambil tulang lalu memakannya. Nyam!
    - MULTI-DOGI: tambah teman dengan warna acak; kalau dua Dogi
      berpapasan, mereka saling menyapa dengan gembira
    - SUARA GONGGONGAN asli (file WAV disintesis otomatis saat pertama
      dijalankan — tanpa file eksternal, tanpa library tambahan)
    - Pomodoro 25 menit + pengingat peregangan tiap 45 menit
    - Catatan lokal dengan tombol Rapikan AI yang bersifat opt-in
    - Google Calendar read-only dengan pengingat agenda melalui Dogi
    - Integrasi CLAUDE CODE: muka mikir "..." saat agent bekerja,
      semua Dogi lompat + menggonggong saat tugas selesai
      (setup: lihat dogi_hook.py & README)
    - 6 tema warna, tersimpan otomatis di ~/.dogi/config.json

Interaksi:
    - Klik Dogi    -> elus (muncul hati)
    - Drag         -> pindahkan posisi
    - Klik kanan   -> menu lengkap

Tested: Windows 10/11. pynput opsional.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from datetime import datetime
import os
import random
import sys
import json
import time
import math
import wave
import struct
import threading
import pathlib
import webbrowser

import agent_hooks
from calendar_integration import (
    CalendarIntegrationError,
    GoogleCalendarIntegration,
    reminder_due,
)
import dogi_hook
from notes_ai import DEFAULT_AI_MODEL, NotesStore, organize_note
from secure_store import SecureStore, SecureStoreError
import startup as startup_registry
from build_info import BUILD_ID
from updater import RELEASE_PAGE, UpdateInfo, UpdateManager, launch_installer
from version import VERSION

if sys.platform.startswith("win"):
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass

try:
    from pynput import keyboard as _pynput_keyboard
    from pynput import mouse as _pynput_mouse
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# ---------------------------------------------------------------- konfigurasi
SCALE = 5
TICK_MS = 110
WALK_SPEED = 3
VWALK_SPEED = 2            # kecepatan jalan vertikal (naik/turun layar)
VCHASE_SPEED = 6
FETCH_SPEED = 7
CHASE_SPEED = 9
ZOOM_SPEED = 12
POUNCE_SPEED = 13
CHASE_RANGE = 350
CURSOR_GLANCE_RANGE = 700
CURSOR_REACTION_COOLDOWN = 1.8
CURSOR_CHASE_COOLDOWN = 14.0
CURSOR_CHASE_CHANCE = 0.16
CURSOR_POUNCE_CHANCE = 0.12   # peluang menerkam kursor, bukan cuma melirik
ROAM_TOP_MARGIN = 80       # batas atas jelajah agar tidak menutupi menu bar
ROAM_BOTTOM_MARGIN = 40
MISCHIEF_MIN_GAP = 55.0    # jeda minimal antar keusilan spontan (detik)
MISCHIEF_MAX_GAP = 120.0
THINK_WATCHDOG_S = 300.0        # auto-lepas dari 'think' bila status nyangkut
THINK_STARTUP_FRESH_S = 120.0   # status 'thinking' lama saat start diabaikan
TRANSPARENT = "#ff00fe"

# Pesan usil Dogi (dipakai perilaku keusilan & terkam kursor)
POUNCE_MESSAGES = (
    "Hap! Dapat kursornya!",
    "Kena kamu! :P",
    "Awas, kuterkam!",
)
MISCHIEF_MESSAGES = (
    "Main dulu yuk, jangan kerja terus~",
    "Bosen nih, temani aku dong!",
    "Ssst... lihat aku, lihat aku!",
    "Ayo lempar bola!",
    "Aku mau kabur bawa sandalmu :P",
    "Kejar aku kalau bisa!",
)
SPIN_MESSAGES = ("Ekorku! Ekorku!", "Muter muter~", "Gak ketangkep-tangkep!")
SNIFF_MESSAGES = ("Sniff... sniff...", "Bau apa ini?", "Hmm, menarik!")
PEE_MESSAGES = ("Pipis dulu ya~", "Ssss...", "Nandain wilayah!")

GRID_W, GRID_H = 16, 12
PIXEL_SPR_W, PIXEL_SPR_H = GRID_W * SCALE, GRID_H * SCALE
SPR_W, SPR_H = 160, 140
BUBBLE_H = 36
CANVAS_W = 230
CANVAS_H = BUBBLE_H + SPR_H
SPR_X = (CANVAS_W - PIXEL_SPR_W) // 2
SPR_Y = BUBBLE_H

POMODORO_MIN = 25
BREAK_MIN = 5
STRETCH_EVERY_MIN = 45
MAX_PETS = 4
FRIEND_DIST = 130          # jarak px agar dua Dogi saling menyapa
FRIEND_COOLDOWN = 25       # detik jeda antar sapaan

CONF_DIR = pathlib.Path.home() / ".dogi"
CONF_FILE = CONF_DIR / "config.json"
STATUS_FILE = CONF_DIR / "agent_status.json"
NOTES_FILE = CONF_DIR / "notes.json"
CREDENTIALS_FILE = CONF_DIR / "credentials.bin"
CALENDAR_SYNC_SECONDS = 300
CALENDAR_RETRY_SECONDS = 60
DEFAULT_CALENDAR_REMINDER_MIN = 10
_SINGLE_INSTANCE_MUTEX = None
_SINGLE_INSTANCE_LOCK = None
_SINGLE_INSTANCE_PID_FILE = CONF_DIR / "dogipet.pid"


def resource_path(*parts):
    """Resolve bundled assets in source runs and PyInstaller builds."""
    base = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def windows_pid_running(pid):
    """True jika PID Windows masih hidup dan bisa dibuka."""
    if not sys.platform.startswith("win") or pid <= 0:
        return False
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    except Exception:
        return False


def acquire_single_instance(smoke_test=False):
    """Pastikan hanya satu DogiPet interaktif yang berjalan di Windows."""
    global _SINGLE_INSTANCE_MUTEX, _SINGLE_INSTANCE_LOCK
    if smoke_test or not sys.platform.startswith("win"):
        return True
    try:
        import atexit
        import os

        CONF_DIR.mkdir(exist_ok=True)
        lock_path = _SINGLE_INSTANCE_PID_FILE
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
        while True:
            try:
                fd = os.open(str(lock_path), flags)
                break
            except FileExistsError:
                try:
                    pid = int(lock_path.read_text(encoding="ascii").strip())
                except Exception:
                    pid = 0
                if pid and windows_pid_running(pid):
                    return False
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
        _SINGLE_INSTANCE_LOCK = fd
        os.write(fd, str(os.getpid()).encode("ascii"))

        def release_lock():
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                if lock_path.read_text(encoding="ascii").strip() == str(os.getpid()):
                    lock_path.unlink()
            except OSError:
                pass

        atexit.register(release_lock)
        return True
    except Exception:
        # Jika PID-file gagal karena izin/path aneh, jatuh ke mutex Windows.
        pass
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p,
        ]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(
            None, False, "Local\\DogiPetDesktopCompanion"
        )
        if not handle:
            return True
        _SINGLE_INSTANCE_MUTEX = handle
        return kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def virtual_desktop_bounds(root):
    """Return the whole Windows desktop, including monitors left/above zero."""
    if sys.platform.startswith("win"):
        try:
            user32 = ctypes.windll.user32
            left = int(user32.GetSystemMetrics(76))
            top = int(user32.GetSystemMetrics(77))
            width = int(user32.GetSystemMetrics(78))
            height = int(user32.GetSystemMetrics(79))
            if width > 0 and height > 0:
                return left, top, left + width, top + height
        except (AttributeError, NameError, OSError, ValueError):
            pass
    width = int(root.winfo_screenwidth())
    height = int(root.winfo_screenheight())
    return 0, 0, width, height


def app_desktop_bounds(app):
    """Compatibility helper for tests and older app objects."""
    left = int(getattr(app, "screen_left", 0))
    top = int(getattr(app, "screen_top", 0))
    right = int(getattr(app, "screen_right", left + app.screen_w))
    bottom = int(getattr(app, "screen_bottom", top + app.screen_h))
    return left, top, right, bottom


def window_geometry(width, height, x, y):
    """Tk geometry with explicit signs, required for negative monitor coords."""
    return f"{int(width)}x{int(height)}{int(x):+d}{int(y):+d}"

# gaya gonggongan: deretan (frek awal, frek akhir, durasi, volume)
BARK_STYLES = {
    "klasik": ((650, 280, 0.10, 0.90), (560, 240, 0.13, 0.90)),
    "kecil":  ((950, 520, 0.07, 0.75), (1050, 560, 0.06, 0.75)),
    "besar":  ((360, 150, 0.18, 1.00), (320, 140, 0.20, 1.00)),
}
SOUND_CHOICES = ("klasik", "kecil", "besar", "senyap")
DEFAULT_SOUND = "klasik"

COLOR_THEMES = {
    "Shiba":  {"o": "#e8a44c", "c": "#f6ddb0", "k": "#5a3a21"},
    "Husky":  {"o": "#9aa7b5", "c": "#f2f2f2", "k": "#3d4653"},
    "Coklat": {"o": "#8a5a33", "c": "#c99a6b", "k": "#4a2d14"},
    "Hitam":  {"o": "#454545", "c": "#9a9a9a", "k": "#141414"},
    "Golden": {"o": "#e6c46a", "c": "#f7ecc7", "k": "#7a5a1f"},
    "Putih":  {"o": "#f4f0e6", "c": "#ffffff", "k": "#9a938a"},
}

FIXED_COLORS = {
    "n": "#2b1c10",  # mata
    "N": "#2b1c10",  # hidung
    "p": "#f2748c",  # lidah
    "r": "#ff5a79",  # hati
    "z": "#7fb4e8",  # Zzz
    "w": "#efe9dc",  # tulang
    "d": "#a8865c",  # tanah/debu galian
    ".": None,
}

# ------------------------------------------------ kebutuhan & jam biologis
STAT_MAX = 100.0
DEFAULT_STATS = {"kenyang": 80.0, "energi": 80.0, "senang": 80.0}
KENYANG_TURUN_PER_MENIT = 100 / 240   # kenyang habis dalam ~4 jam
ENERGI_TURUN_PER_MENIT = 100 / 360    # energi habis ~6 jam terjaga
ENERGI_PULIH_PER_MENIT = 100 / 60     # tidur 1 jam memulihkan penuh
SENANG_TURUN_PER_MENIT = 100 / 480    # kangen dielus setelah ~8 jam
OFFLINE_DECAY_FACTOR = 0.25           # waktu offline dihitung lebih ringan
OFFLINE_FLOOR = 25.0                  # decay offline tidak menghukum terlalu dalam
NEED_LOW = 30                         # di bawah ini Dogi mulai minta perhatian
NAG_COOLDOWN = 120                    # detik jeda antar rengekan
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6
MORNING_START_HOUR = 6
MORNING_END_HOUR = 11
LUNCH_HOUR = 12


def clamp_stat(value):
    return max(0.0, min(STAT_MAX, float(value)))


def decay_stats(stats, minutes, sleeping=False):
    """Hitung stat baru setelah `minutes` menit; tidur memulihkan energi."""
    if minutes <= 0:
        return dict(stats)
    kenyang_rate = KENYANG_TURUN_PER_MENIT * (0.5 if sleeping else 1.0)
    energi_delta = (
        ENERGI_PULIH_PER_MENIT if sleeping else -ENERGI_TURUN_PER_MENIT
    ) * minutes
    return {
        "kenyang": clamp_stat(stats["kenyang"] - kenyang_rate * minutes),
        "energi": clamp_stat(stats["energi"] + energi_delta),
        "senang": clamp_stat(stats["senang"] - SENANG_TURUN_PER_MENIT * minutes),
    }


def offline_decay(stats, minutes):
    """Decay ringan selama aplikasi tertutup, dengan batas bawah yang ramah."""
    decayed = decay_stats(stats, minutes * OFFLINE_DECAY_FACTOR)
    return {
        key: max(decayed[key], min(clamp_stat(stats[key]), OFFLINE_FLOOR))
        for key in decayed
    }


def is_night(hour):
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


def is_morning(hour):
    return MORNING_START_HOUR <= hour < MORNING_END_HOUR


# --------------------------------------------------- deteksi kerja nonstop
REST_IDLE_RESET_S = 5 * 60    # jeda input selama ini dihitung sudah istirahat
REST_NAG_EVERY_S = 10 * 60    # ulangi ajakan tiap 10 menit bila masih lanjut
REST_CHOICES = (45, 60, 90)   # pilihan ambang menit nonstop

# ---------------------------------------------- reaksi scroll & video meeting
SCROLL_REACTION_SECONDS = 0.9
CURSOR_SWING_MIN_RUN = 130
CURSOR_SWING_WINDOW_SECONDS = 2.4
CURSOR_SWING_REVERSALS = 7
DIZZY_COOLDOWN_SECONDS = 30.0
MEETING_POLL_SECONDS = 2.0
MEETING_LOST_GRACE_SECONDS = 8.0
MEETING_WATCH_EVERY_SECONDS = 3 * 60

MEETING_BROWSER_EXES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
    "vivaldi.exe", "arc.exe",
}
MEETING_EXES = {
    "zoom.exe", "teams.exe", "ms-teams.exe", "webex.exe", "webexmta.exe",
    "skype.exe", "slack.exe", "discord.exe", "around.exe",
    "ringcentral.exe", "gotomeeting.exe", "bluejeans.exe",
}
MEETING_TITLE_MARKERS = (
    "zoom meeting",
    "google meet",
    "meet - ",
    "microsoft teams meeting",
    "meeting | microsoft teams",
    "webex meeting",
    "webex webinar",
    "slack huddle",
    "discord call",
    "jitsi meet",
    "whereby",
    "ringcentral video",
    "gotomeeting",
    "around meeting",
    "bluejeans meeting",
)


def is_meeting_window(executable, title):
    """Heuristik konservatif untuk jendela meeting yang benar-benar terlihat."""
    executable = pathlib.Path(str(executable or "")).name.lower()
    title = str(title or "").strip().lower()
    if not title:
        return False
    if any(marker in title for marker in MEETING_TITLE_MARKERS):
        return executable in MEETING_EXES or executable in MEETING_BROWSER_EXES
    if executable == "zoom.exe":
        return "meeting" in title or "webinar" in title
    if executable in {"teams.exe", "ms-teams.exe"}:
        return "meeting" in title or "call" in title
    if executable in {"webex.exe", "webexmta.exe", "skype.exe"}:
        return "meeting" in title or "call" in title or "webinar" in title
    if executable in {"slack.exe", "discord.exe"}:
        return "huddle" in title or "call" in title
    if executable in MEETING_EXES:
        return any(word in title for word in ("meeting", "call", "webinar", "huddle"))
    return False


def visible_meeting_windows():
    """Kembalikan jendela meeting Windows tanpa mengambil audio/video/data rapat."""
    if not sys.platform.startswith("win"):
        return []
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        process_query_limited = 0x1000
        candidates = []

        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        enum_callback = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )

        def executable_for_pid(pid):
            handle = kernel32.OpenProcess(process_query_limited, False, pid)
            if not handle:
                return ""
            try:
                size = wintypes.DWORD(1024)
                buffer = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(
                    handle, 0, buffer, ctypes.byref(size)
                ):
                    return pathlib.Path(buffer.value).name
                return ""
            finally:
                kernel32.CloseHandle(handle)

        class Rect(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        @enum_callback
        def collect(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title_buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, length + 1)
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            executable = executable_for_pid(pid.value)
            title = title_buffer.value
            if not is_meeting_window(executable, title):
                return True
            rect = Rect()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            width = max(0, rect.right - rect.left)
            height = max(0, rect.bottom - rect.top)
            if width < 240 or height < 160:
                return True
            candidates.append(
                {
                    "hwnd": int(hwnd),
                    "title": title,
                    "executable": executable,
                    "center_x": rect.left + width // 2,
                    "area": width * height,
                }
            )
            return True

        user32.EnumWindows(collect, 0)
        return sorted(candidates, key=lambda item: item["area"], reverse=True)
    except (AttributeError, OSError, ValueError):
        return []


def rect_covers_monitor(window, monitor, tol=2):
    """True bila persegi jendela menutupi (nyaris) seluruh area monitor."""
    wl, wt, wr, wb = window
    ml, mt, mr, mb = monitor
    return (
        wl <= ml + tol and wt <= mt + tol
        and wr >= mr - tol and wb >= mb - tol
        and (wr - wl) > 0 and (wb - wt) > 0
    )


def foreground_fullscreen_active():
    """Deteksi aplikasi fullscreen di depan (presentasi, video, game, share).

    Hanya membaca geometri jendela terdepan vs monitornya; tidak menyentuh isi
    aplikasi. Jendela shell/desktop dan jendela milik DogiPet sendiri diabaikan.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        class_buffer = ctypes.create_unicode_buffer(96)
        user32.GetClassNameW(hwnd, class_buffer, 96)
        if class_buffer.value in (
            "Progman", "WorkerW", "Shell_TrayWnd", "Windows.UI.Core.CoreWindow",
        ):
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            return False

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", wintypes.DWORD),
            ]

        window_rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
            return False
        monitor = user32.MonitorFromWindow(hwnd, 2)  # DEFAULTTONEAREST
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return False
        m = info.rcMonitor
        return rect_covers_monitor(
            (window_rect.left, window_rect.top,
             window_rect.right, window_rect.bottom),
            (m.left, m.top, m.right, m.bottom),
        )
    except (AttributeError, OSError, ValueError):
        return False


class CursorSwingDetector:
    """Detect deliberate, repeated horizontal cursor reversals."""

    def __init__(
        self,
        min_run=CURSOR_SWING_MIN_RUN,
        window=CURSOR_SWING_WINDOW_SECONDS,
        reversals=CURSOR_SWING_REVERSALS,
        cooldown=DIZZY_COOLDOWN_SECONDS,
    ):
        self.min_run = min_run
        self.window = window
        self.reversals = reversals
        self.cooldown = cooldown
        self.last_x = None
        self.direction = 0
        self.run_distance = 0
        self.reversal_times = []
        self.cooldown_until = 0.0

    def update(self, x, now):
        if self.last_x is None:
            self.last_x = x
            return 0, False
        delta = x - self.last_x
        self.last_x = x
        if abs(delta) < 5:
            return 0, False
        direction = 1 if delta > 0 else -1
        if not self.direction:
            self.direction = direction
            self.run_distance = abs(delta)
        elif direction == self.direction:
            self.run_distance += abs(delta)
        else:
            if self.run_distance >= self.min_run:
                self.reversal_times.append(now)
            self.direction = direction
            self.run_distance = abs(delta)
        self.reversal_times = [
            timestamp for timestamp in self.reversal_times
            if now - timestamp <= self.window
        ]
        triggered = (
            len(self.reversal_times) >= self.reversals
            and now >= self.cooldown_until
        )
        if triggered:
            self.reversal_times.clear()
            self.cooldown_until = now + self.cooldown
        return direction, triggered


class ActivityMonitor:
    """Melacak berapa menit pengguna aktif beruntun di komputer.

    Aktif = ada input keyboard/mouse. Jeda input sepanjang `idle_reset_s`
    dianggap istirahat dan memulai sesi baru.
    """

    def __init__(self, idle_reset_s=REST_IDLE_RESET_S):
        self.idle_reset_s = idle_reset_s
        self.session_start = None
        self.last_activity = None

    def update(self, now, active):
        """Catat kondisi saat ini; kembalikan menit aktif beruntun."""
        if active:
            if (
                self.last_activity is None
                or now - self.last_activity >= self.idle_reset_s
            ):
                self.session_start = now
            self.last_activity = now
        elif (
            self.last_activity is not None
            and now - self.last_activity >= self.idle_reset_s
        ):
            self.session_start = None
        if self.session_start is None:
            return 0.0
        return (now - self.session_start) / 60


# ------------------------------------------------------------------ sprite art
# Grid 16x12, menghadap KANAN. 'n' mata (bergerak), 'N' hidung.

IDLE_1 = [
    "..........kk.kk.",
    ".k........kokkok",
    ".kk.......koooo.",
    "..kk...kooooooo.",
    "...koooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooook..",
    "....kockookcok..",
    "....kok....kok..",
    "....kk......kk..",
    "................",
]

IDLE_2 = [
    "..........kk.kk.",
    "..........kokkok",
    ".k........koooo.",
    ".kk....kooooooo.",
    "..kkoooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooook..",
    "....kockookcok..",
    "....kok....kok..",
    "....kk......kk..",
    "................",
]

WALK_1 = [
    "..........kk.kk.",
    ".k........kokkok",
    ".kk.......koooo.",
    "..kk...kooooooo.",
    "...koooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooook..",
    "...kockookcok...",
    "...kok.....kok..",
    "...kk.......kk..",
    "................",
]

WALK_2 = [
    "..........kk.kk.",
    "..........kokkok",
    ".k........koooo.",
    ".kk....kooooooo.",
    "..kkoooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooook..",
    ".....kockookcok.",
    ".....kok....kok.",
    "......kk.....kk.",
    "................",
]

SLEEP_1 = [
    "................",
    "................",
    "................",
    "..........z..z..",
    "...........zz...",
    ".k........kk.kk.",
    ".kk......kokkok.",
    "..kkoooookoooo..",
    "..koooooooooook.",
    "..kooccooooccok.",
    "..kkkkkkkkkkkk..",
    "................",
]

SLEEP_2 = [
    "................",
    "................",
    "..........z.z...",
    "...........z....",
    "................",
    ".k........kk.kk.",
    ".kk......kokkok.",
    "..kkoooookoooo..",
    "..koooooooooook.",
    "..kooccooooccok.",
    "..kkkkkkkkkkkk..",
    "................",
]

HAPPY_1 = [
    "....r.r...kk.kk.",
    ".k..rrr...kokkok",
    ".kk..r....koooo.",
    "..kk...kooooooo.",
    "...koooooonoono.",
    "....koooooccccN.",
    "....kooooooccpp.",
    "....kooooooook..",
    "....kockookcok..",
    "....kok....kok..",
    "....kk......kk..",
    "................",
]

HAPPY_2 = [
    "..r.r.....kk.kk.",
    "..rrr.....kokkok",
    ".k.r......koooo.",
    ".kk....kooooooo.",
    "..kkoooooonoono.",
    "....koooooccccN.",
    "....kooooooccpp.",
    "....kooooooook..",
    "....kockookcok..",
    "....kok....kok..",
    "....kk......kk..",
    "................",
]

# Menggali: kaki depan mencakar tanah, debu beterbangan
DIG_1 = [
    "..........kk.kk.",
    ".k........kokkok",
    ".kk.......koooo.",
    "..kk...kooooooo.",
    "...koooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooook..",
    "....kockook.....",
    "....kok...kkk...",
    "....kk.....kk.d.",
    "..........d..d..",
]

DIG_2 = [
    "..........kk.kk.",
    "..........kokkok",
    ".k........koooo.",
    ".kk....kooooooo.",
    "..kkoooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooook..",
    "....kockookck...",
    "....kok....k.k..",
    "....kk......kkd.",
    ".........d....d.",
]

# Makan tulang: tulang putih di mulut, mengunyah
EAT_1 = [
    "..........kk.kk.",
    ".k........kokkok",
    ".kk.......koooo.",
    "..kk...kooooooo.",
    "...koooooonoono.",
    "....koooooccccN.",
    "....koooooocwww.",
    "....kooooooowkww",
    "....kockookcok..",
    "....kok....kok..",
    "....kk......kk..",
    "................",
]

EAT_2 = [
    "..........kk.kk.",
    "..........kokkok",
    ".k........koooo.",
    ".kk....kooooooo.",
    "..kkoooooonoono.",
    "....koooooccccN.",
    "....kooooooccww.",
    "....koooooookww.",
    "....kockookcok..",
    "....kok....kok..",
    "....kk......kk..",
    "................",
]

# Diangkat: Dogi menggantung kaget saat diseret, kaki berayun-ayun.
HOLD_1 = [
    "..........kk.kk.",
    "..........kokkok",
    "..........koooo.",
    ".......kooooooo.",
    ".......koonoono.",
    ".......kooccccN.",
    ".......kooocccp.",
    ".......koooook..",
    ".......kooook...",
    ".......kok.kok..",
    ".......kk...kk..",
    "................",
]

HOLD_2 = [
    "..........kk.kk.",
    "..........kokkok",
    "..........koooo.",
    ".......kooooooo.",
    ".......koonoono.",
    ".......kooccccN.",
    ".......kooocccp.",
    ".......koooook..",
    ".......kooook...",
    ".......kok..kok.",
    ".......kk....kk.",
    "................",
]

# Ikut mengetik: laptop mini di depan Dogi, kaki depan bergantian menekan
# tombol. Layar memakai warna 'z' agar tampak menyala.
TYPE_1 = [
    "..........kk.kk.",
    ".k........kokkok",
    ".kk.......koooo.",
    "..kk...kooooooo.",
    "...koooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooookzw",
    "....kockoo.ko.zw",
    "....kok.....kozw",
    "....kk...wwwwwww",
    "................",
]

TYPE_2 = [
    "..........kk.kk.",
    ".k........kokkok",
    ".kk.......koooo.",
    "..kk...kooooooo.",
    "...koooooonoono.",
    "....koooooccccN.",
    "....koooooocccp.",
    "....kooooooookzw",
    "....kockoo..kozw",
    "....kok....ko.zw",
    "....kk...wwwwwww",
    "................",
]

# Scroll: Dogi memakai laptop mininya, dengan indikator posisi scroll ('r')
# bergerak dari atas ke bawah. Arah naik memakai urutan frame terbalik.
SCROLL_TOP = [
    row[:-1] + "r" if index == 7 else row
    for index, row in enumerate(TYPE_1)
]
SCROLL_BOTTOM = [
    row[:-1] + "r" if index == 9 else row
    for index, row in enumerate(TYPE_2)
]

# Meeting: pose gembira diubah menjadi waspada; gelombang 'z' menandai suara
# gonggongan, sementara pose watch tetap tenang dan menatap jendela meeting.
MEETING_ALERT_1 = [row.replace("r", "z") for row in HAPPY_1]
MEETING_ALERT_2 = [row.replace("r", "z") for row in HAPPY_2]

FRAMES = {
    "idle":  [IDLE_1, IDLE_2],
    "walk":  [WALK_1, WALK_2],
    "chase": [WALK_1, WALK_2],
    "fetch": [WALK_1, WALK_2],
    "sleep": [SLEEP_1, SLEEP_2],
    "happy": [HAPPY_1, HAPPY_2],
    "dig":   [DIG_1, DIG_2],
    "eat":   [EAT_1, EAT_2],
    "hold":  [HOLD_1, HOLD_2],
    "type":  [TYPE_1, TYPE_2],
    "scroll_up": [SCROLL_BOTTOM, SCROLL_TOP],
    "scroll_down": [SCROLL_TOP, SCROLL_BOTTOM],
    "meeting_alert": [MEETING_ALERT_1, MEETING_ALERT_2],
    "meeting_watch": [IDLE_1, IDLE_2],
    "think": [IDLE_1, IDLE_1],
    "jump":  [HAPPY_1, HAPPY_2],
    "dizzy": [IDLE_1, IDLE_2],
    "curious": [IDLE_1, IDLE_2],
    "tail_wag": [DIG_1, DIG_2],
    "beg": [HAPPY_1, HAPPY_2],
    "zoomies": [WALK_1, WALK_2],
    "glance": [IDLE_1, IDLE_2],
    "spin": [WALK_1, WALK_2],
    "pounce": [WALK_1, WALK_2],
    "sniff": [DIG_1, DIG_2],
    "pee": [DIG_1, DIG_2],
}

# Raster sprites imported from the user-approved reference sheet.  FRAMES stays
# as a safe fallback for old/source-only installs, while normal builds use these
# richer 4-5 frame PNG animations.
SPRITE_FRAME_COUNTS = {
    "idle": 4,
    "walk": 4,
    "chase": 4,
    "fetch": 4,
    "sleep": 4,
    "happy": 4,
    "dig": 4,
    "eat": 4,
    "hold": 4,
    "type": 8,
    "scroll_up": 4,
    "scroll_down": 4,
    "meeting_alert": 4,
    "meeting_watch": 4,
    "think": 4,
    "tail_wag": 4,
    "jump": 4,
    "dizzy": 4,
    "pee": 4,
}
# Seluruh sprite hasil draw_sprites.py digambar menghadap KANAN, jadi tidak ada
# state yang "asli menghadap kiri". Sprite hanya dicerminkan saat Dogi bergerak
# ke kiri. (Dulu set ini berisi walk/chase/dsb. warisan lembar sprite lama yang
# menghadap kiri, sehingga arah jalan tampak terbalik.)
SPRITE_NATIVE_LEFT = set()
SPRITE_FRAME_SEQUENCES = {
    # Kembali melewati frame tengah agar kepala tidak melompat dari kanan
    # langsung ke kiri saat siklus animasi bingung dimulai ulang.
    "think": (0, 1, 2, 3, 2, 1),
}
SPRITE_FRAME_HOLD = {"think": 2}
SPRITE_STATE_ASSET = {
    "curious": "think",
    "glance": "think",
    "beg": "happy",
    "zoomies": "chase",
    "spin": "chase",
    "pounce": "chase",
    "sniff": "dig",
}


def sprite_asset_state(state):
    return SPRITE_STATE_ASSET.get(state, state)


def sprite_frame_index(state, tick):
    """Return an animation frame with optional ping-pong and frame holding."""
    state = sprite_asset_state(state)
    count = SPRITE_FRAME_COUNTS.get(state, 1)
    sequence = SPRITE_FRAME_SEQUENCES.get(state, tuple(range(count)))
    hold = SPRITE_FRAME_HOLD.get(state, 1)
    return sequence[(tick // hold) % len(sequence)]


def sprite_is_mirrored(state, facing):
    """Mirror when requested facing differs from the source artwork."""
    state = sprite_asset_state(state)
    native_left = state in SPRITE_NATIVE_LEFT
    return facing == (1 if native_left else -1)

JUMP_ARC = [6, 14, 22, 26, 26, 22, 14, 6, 0]

BONE_SPRITE = [
    "ww......ww",
    "wwwwwwwwww",
    "wwwwwwwwww",
    "ww......ww",
]
BONE_SCALE = 4
BONE_W = len(BONE_SPRITE[0]) * BONE_SCALE
BONE_H = len(BONE_SPRITE) * BONE_SCALE


def mirror(frame):
    return [row[::-1] for row in frame]


# ---------------------------------------------------------------- suara
def bark_file(style):
    return CONF_DIR / f"bark-{style}.wav"


def ensure_bark_wav(style=DEFAULT_SOUND):
    """Sintesis file WAV gonggongan untuk gaya tertentu bila belum ada."""
    bursts = BARK_STYLES.get(style)
    if not bursts or bark_file(style).exists():
        return
    try:
        CONF_DIR.mkdir(exist_ok=True)
        sr = 22050
        samples = []

        def burst(f0, f1, dur, vol):
            n = int(sr * dur)
            for i in range(n):
                t = i / sr
                f = f0 + (f1 - f0) * (i / n)          # pitch turun
                env = math.sin(math.pi * i / n) ** 0.5  # attack-decay
                v = vol * env * (
                    0.55 * math.sin(2 * math.pi * f * t)
                    + 0.30 * math.sin(4 * math.pi * f * t)
                    + 0.15 * math.sin(6 * math.pi * f * t)
                )
                samples.append(int(max(-1.0, min(1.0, v)) * 32767))

        for index, params in enumerate(bursts):
            if index:
                samples.extend([0] * int(sr * 0.06))  # jeda antar "guk"
            burst(*params)

        with wave.open(str(bark_file(style)), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    except Exception:
        pass


def bark(root, style=DEFAULT_SOUND):
    if style == "senyap":
        return

    def _go():
        try:
            path = bark_file(style)
            if HAS_SOUND and path.exists():
                winsound.PlaySound(
                    str(path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC,
                )
            elif HAS_SOUND:
                winsound.Beep(520, 70)
                winsound.Beep(420, 90)
            else:
                root.bell()
        except Exception:
            pass
    threading.Thread(target=_go, daemon=True).start()


# ---------------------------------------------------------------- tulang
class Bone:
    """Tulang kecil di layar yang menunggu diambil Dogi."""

    def __init__(self, app, x, y):
        self.app = app
        self.x, self.y = x, y
        self.win = tk.Toplevel(app.root)
        self.win.title("DogiPet Bone")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        if app.transparent_ok:
            try:
                self.win.attributes("-transparentcolor", TRANSPARENT)
            except tk.TclError:
                pass
        bg = TRANSPARENT if app.transparent_ok else "#222222"
        cv = tk.Canvas(
            self.win, width=BONE_W, height=BONE_H, bg=bg,
            highlightthickness=0, bd=0,
        )
        cv.pack()
        for gy, row in enumerate(BONE_SPRITE):
            for gx, ch in enumerate(row):
                if ch == "w":
                    x0, y0 = gx * BONE_SCALE, gy * BONE_SCALE
                    cv.create_rectangle(
                        x0, y0, x0 + BONE_SCALE, y0 + BONE_SCALE,
                        fill=FIXED_COLORS["w"], outline="#c9c2b2",
                    )
        self.win.geometry(window_geometry(BONE_W, BONE_H, x, y))

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------- satu Dogi
class DogiPet:
    def __init__(self, app, x, theme, primary=False):
        self.app = app
        self.primary = primary
        self.theme = theme

        self.win = tk.Toplevel(app.root)
        self.win.title("DogiPet")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        if app.transparent_ok:
            try:
                self.win.attributes("-transparentcolor", TRANSPARENT)
            except tk.TclError:
                pass
        bg = TRANSPARENT if app.transparent_ok else "#222222"
        self.canvas = tk.Canvas(
            self.win, width=CANVAS_W, height=CANVAS_H, bg=bg,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack()

        self.x = x
        _, _, _, screen_bottom = app_desktop_bounds(app)
        self.ground_y = screen_bottom - CANVAS_H - 60
        self.y = self.ground_y

        self.state = "idle"
        self.state_timer = random.randint(20, 50)
        self.frame_i = random.randint(0, 1)
        self.facing = random.choice([1, -1])
        self.motion_facing = self.facing
        self.target_x = x
        self.target_y = self.ground_y
        self.blink = False
        self.temp_msg = None
        self.fetch_bone = None
        self._sprite_cache = {}
        self.gaze_x = self.center_x()
        self.gaze_y = self.y + SPR_Y
        self.gaze_until = 0.0
        self.cursor_reaction_until = 0.0
        self.chase_cooldown_until = 0.0

        self._drag_start = None
        self._moved = False
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_menu)

        self.place()

    # ------------------------------------------------------------- utilitas
    def center_x(self):
        return self.x + CANVAS_W // 2

    def _roam_bounds(self):
        """Rentang y yang boleh dijelajahi Dogi (jalan vertikal)."""
        _, screen_top, _, screen_bottom = app_desktop_bounds(self.app)
        top = screen_top + ROAM_TOP_MARGIN
        bottom = screen_bottom - CANVAS_H - ROAM_BOTTOM_MARGIN
        return top, max(top, bottom)

    def _random_roam_target(self, margin=80):
        left, _, right, _ = app_desktop_bounds(self.app)
        min_x = left + margin
        max_x = max(min_x, right - CANVAS_W - margin)
        top, bottom = self._roam_bounds()
        return random.randint(min_x, max_x), random.randint(top, bottom)

    def _step_axis(self, current, target, speed):
        delta = target - current
        if abs(delta) > speed:
            return current + speed * (1 if delta > 0 else -1)
        return target

    def place(self):
        self.win.geometry(window_geometry(CANVAS_W, CANVAS_H, self.x, self.y))

    def palette(self):
        pal = dict(FIXED_COLORS)
        pal.update(COLOR_THEMES[self.theme])
        return pal

    def set_state(self, state, duration=None):
        # Setelah tulang ditugaskan, Dogi harus menyelesaikan pengambilannya.
        # Notifikasi global (agent selesai, meeting, sapaan jam, dan perilaku
        # spontan) dapat memanggil set_state di antara dua tick. Dulu panggilan
        # itu membatalkan fetch dan meninggalkan tulang sendirian di layar.
        if self.state == "fetch" and self.fetch_bone is not None \
                and state not in ("fetch", "hold", "eat"):
            return
        if self.state == "fetch" and state not in ("fetch", "hold"):
            self.fetch_bone = None
        self.state = state
        self.frame_i = 0
        if duration is None:
            duration = {
                "idle":  random.randint(20, 50),
                "walk":  random.randint(25, 60),
                "sleep": random.randint(80, 160),
                "happy": 14,
                "chase": 60,
                "fetch": 999999,
                "dig":   20,
                "hold":  999999,
                "type":  20,
                "scroll_up": 14,
                "scroll_down": 14,
                "meeting_alert": 36,
                "meeting_watch": 24,
                "eat":   22,
                "think": 999999,
                "jump":  len(JUMP_ARC),
                "dizzy": 44,
                "curious": 36,
                "tail_wag": 28,
                "beg": 24,
                "zoomies": 999999,
                "glance": 14,
                "spin": 30,
                "pounce": 45,
                "sniff": 26,
                "pee": 30,
            }[state]
        self.state_timer = duration
        if state == "walk":
            self.target_x, self.target_y = self._random_roam_target(80)
            self.facing = 1 if self.target_x > self.x else -1
            self.motion_facing = self.facing
        elif state == "zoomies":
            margin = 40
            left, _, right, _ = app_desktop_bounds(self.app)
            middle = (left + right) // 2
            self.target_x = (
                right - CANVAS_W - margin
                if self.center_x() < middle
                else left + margin
            )
            top, bottom = self._roam_bounds()
            self.target_y = random.randint(top, bottom)
            self.facing = 1 if self.target_x > self.x else -1
            self.motion_facing = self.facing

    def visual_facing(self):
        if self.state in ("walk", "chase", "fetch", "zoomies"):
            return self.motion_facing
        return self.facing

    def _record_motion_facing(self, previous_x):
        if self.x > previous_x:
            self.motion_facing = 1
        elif self.x < previous_x:
            self.motion_facing = -1

    def show_msg(self, text, seconds=5):
        self.temp_msg = (text, time.time() + seconds)

    def celebrate(self, msg=None):
        if msg:
            self.show_msg(msg, 6)
        self.y = self.ground_y
        self.set_state("jump")

    # -------------------------------------------------------------- gambar
    def _shift_eyes(self, frame, cx, cy):
        grid = [list(r) for r in frame]
        eyes = [
            (gx, gy)
            for gy, row in enumerate(grid)
            for gx, ch in enumerate(row)
            if ch == "n"
        ]
        if not eyes:
            return frame
        dog_cx = self.center_x()
        dog_cy = self.y + SPR_Y + SPR_H // 3
        dx = 0 if abs(cx - dog_cx) < 50 else (1 if cx > dog_cx else -1)
        dy = 0 if abs(cy - dog_cy) < 50 else (1 if cy > dog_cy else -1)
        for (gx, gy) in eyes:
            grid[gy][gx] = "o"
        if not self.blink:
            for (gx, gy) in eyes:
                nx, ny = gx + dx, gy + dy
                if 0 <= ny < GRID_H and 0 <= nx < GRID_W \
                        and grid[ny][nx] == "o":
                    grid[ny][nx] = "n"
                else:
                    grid[gy][gx] = "n"
        return ["".join(r) for r in grid]

    def _bubble_text(self):
        now = time.time()
        if self.state == "think" and self.primary:
            return ". . ."
        if self.temp_msg:
            if now < self.temp_msg[1]:
                return self.temp_msg[0]
            self.temp_msg = None
        if self.primary and self.app.pomo_end:
            rem = max(0, int(self.app.pomo_end - now))
            return f"{rem // 60:02d}:{rem % 60:02d}"
        return None

    def _sprite_image(self):
        asset_state = sprite_asset_state(self.state)
        count = SPRITE_FRAME_COUNTS.get(asset_state, 0)
        if not count:
            return None
        if self.state == "glance":
            # Asset think memiliki mata kiri/atas/kanan. Pilih satu pose dari
            # arah kursor tanpa membalik atau menggeser seluruh badan Dogi.
            horizontal = (self.gaze_x - self.center_x()) * self.visual_facing()
            head_y = self.y + SPR_Y + SPR_H * 0.35
            frame_index = (
                1 if self.gaze_y < head_y - 30
                else (2 if horizontal >= 0 else 0)
            )
        else:
            frame_index = sprite_frame_index(asset_state, self.frame_i)
        mirrored = sprite_is_mirrored(self.state, self.visual_facing())
        key = (self.theme, self.state, frame_index, mirrored)
        if key in self._sprite_cache:
            return self._sprite_cache[key]
        suffix = "_left" if mirrored else ""
        path = resource_path(
            "assets", "sprites", self.theme.lower(),
            f"{asset_state}_{frame_index}{suffix}.png",
        )
        try:
            image = tk.PhotoImage(file=str(path))
        except tk.TclError:
            image = None
        self._sprite_cache[key] = image
        return image

    def draw(self, cx, cy):
        self.canvas.delete("all")
        pal = self.palette()
        sprite = self._sprite_image()
        if sprite is not None:
            self.canvas.create_image(
                CANVAS_W // 2, SPR_Y + SPR_H,
                image=sprite, anchor="s",
            )
        else:
            frame = FRAMES[self.state][self.frame_i % 2]
            if self.facing == -1 and self.state != "sleep":
                frame = mirror(frame)
            if self.state in (
                "idle", "walk", "chase", "fetch", "think", "dig", "type",
                "scroll_up", "scroll_down", "meeting_watch",
            ):
                frame = self._shift_eyes(frame, cx, cy)
            for gy, row in enumerate(frame):
                for gx, ch in enumerate(row):
                    color = pal.get(ch)
                    if color:
                        x0 = SPR_X + gx * SCALE
                        y0 = SPR_Y + gy * SCALE
                        self.canvas.create_rectangle(
                            x0, y0, x0 + SCALE, y0 + SCALE,
                            fill=color, outline=color,
                        )
        text = self._bubble_text()
        if text:
            w = len(text) * 7 + 18
            x0 = (CANVAS_W - w) // 2
            self.canvas.create_rectangle(
                x0, 4, x0 + w, 28,
                fill="#fffdf5", outline=pal["k"], width=2,
            )
            self.canvas.create_text(
                CANVAS_W // 2, 16, text=text,
                font=("Consolas", 9, "bold"), fill="#333333",
            )

    # ---------------------------------------------------------------- logika
    def tick(self, now, cx, cy, typing, thinking, scrolling=0):
        previous_x = self.x
        # Drag punya prioritas tertinggi: jangan biarkan status agent, typing,
        # atau pergerakan otomatis menimpa pose Dogi yang sedang digendong.
        if self._drag_start and self._moved:
            if self.state != "hold":
                self.set_state("hold")
            self.blink = False
            self.frame_i += 1
            return

        # status agent AI: fokus "think", tapi main lempar tulang tetap boleh
        # menembusnya supaya Dogi tak pernah benar-benar terkunci diam.
        if thinking and self.state not in (
            "think", "jump", "meeting_alert", "fetch", "eat",
        ):
            self.set_state("think")
        elif not thinking and self.state == "think":
            self.set_state("idle")

        # mengetik -> Dogi ikut mengetik di laptop mininya
        if typing and self.state in (
            "idle", "walk", "sleep", "dig",
            "curious", "tail_wag", "beg", "zoomies", "glance",
            "spin", "sniff", "pee",
        ):
            self.set_state("type")
        if self.state == "type" and not typing \
                and now - self.app.last_key_time > 2.0:
            self.set_state("idle")

        # Scroll global -> Dogi menggeser indikator di laptop mini. Setiap arah
        # memiliki urutan frame berbeda agar gerakannya terasa mengikuti roda.
        if scrolling and self.app.scroll_reaction_on and self.state in (
            "idle", "walk", "sleep", "dig", "type",
            "curious", "tail_wag", "beg", "zoomies",
            "scroll_up", "scroll_down", "glance", "spin", "sniff", "pee",
        ):
            scroll_state = "scroll_up" if scrolling > 0 else "scroll_down"
            if self.state != scroll_state:
                self.set_state(scroll_state)
        elif self.state in ("scroll_up", "scroll_down") and not scrolling:
            self.set_state("type" if typing else "idle")

        # Dogi lebih sering hanya melirik. Mengejar adalah reaksi langka dan
        # memiliki cooldown agar gerakan mouse biasa tidak selalu memanggilnya.
        if self.state in ("idle", "walk", "glance"):
            speed = (
                abs(cx - self.app.last_cursor[0])
                + abs(cy - self.app.last_cursor[1])
            )
            dist = math.hypot(
                cx - self.center_x(), cy - (self.y + CANVAS_H // 2)
            )
            if speed > 12 and dist < CURSOR_GLANCE_RANGE:
                self.gaze_x, self.gaze_y = cx, cy
                self.gaze_until = now + 1.8
            if speed > 60 and dist < CURSOR_GLANCE_RANGE \
                    and now >= self.cursor_reaction_until:
                self.cursor_reaction_until = now + CURSOR_REACTION_COOLDOWN
                may_chase = (
                    dist < CHASE_RANGE
                    and now >= self.chase_cooldown_until
                    and random.random() < CURSOR_CHASE_CHANCE
                )
                may_pounce = (
                    not may_chase
                    and dist < CHASE_RANGE
                    and now >= self.chase_cooldown_until
                    and random.random() < CURSOR_POUNCE_CHANCE
                )
                if may_chase:
                    self.chase_cooldown_until = now + CURSOR_CHASE_COOLDOWN
                    self.set_state("chase")
                elif may_pounce:
                    self.chase_cooldown_until = now + CURSOR_CHASE_COOLDOWN
                    self.gaze_x, self.gaze_y = cx, cy
                    self.set_state("pounce")
                elif self.state != "glance":
                    self.set_state("glance")

        # pergerakan (dua sumbu: Dogi bisa jalan mendatar dan vertikal)
        if self.state == "walk":
            self.x = self._step_axis(self.x, self.target_x, WALK_SPEED)
            self.y = self._step_axis(self.y, self.target_y, VWALK_SPEED)
            self.ground_y = self.y
            if self.x == self.target_x and self.y == self.target_y:
                self.set_state("idle")

        elif self.state == "chase":
            target = cx - CANVAS_W // 2
            top, bottom = self._roam_bounds()
            target_y = max(top, min(bottom, cy - SPR_Y - SPR_H // 2))
            self.facing = 1 if target > self.x else -1
            self.x = self._step_axis(self.x, target, CHASE_SPEED)
            self.y = self._step_axis(self.y, target_y, VCHASE_SPEED)
            self.ground_y = self.y
            if self.x == target and self.y == target_y:
                self.set_state("happy")

        elif self.state == "fetch" and self.fetch_bone:
            target = self.fetch_bone.x - CANVAS_W // 2 + BONE_W // 2
            target_y = self.fetch_bone.y - (CANVAS_H - BONE_H - 6)
            top, bottom = self._roam_bounds()
            target_y = max(top, min(bottom, target_y))
            self.facing = 1 if target > self.x else -1
            self.x = self._step_axis(self.x, target, FETCH_SPEED)
            self.y = self._step_axis(self.y, target_y, VCHASE_SPEED)
            self.ground_y = self.y
            if self.x == target and self.y == target_y:
                self.app.remove_bone(self.fetch_bone)
                self.fetch_bone = None
                bark(self.app.root, self.app.sound_style)
                self.show_msg("Nyam nyam!", 3)
                self.set_state("eat")
                self.app.on_fed()

        elif self.state == "zoomies":
            self.facing = 1 if self.target_x > self.x else -1
            self.x = self._step_axis(self.x, self.target_x, ZOOM_SPEED)
            self.y = self._step_axis(self.y, self.target_y, VCHASE_SPEED)
            self.ground_y = self.y
            if self.x == self.target_x and self.y == self.target_y:
                self.show_msg("Wusss!", 2)
                self.set_state("happy")

        elif self.state == "spin":
            # kejar ekor sendiri: badan berputar dengan membalik arah cepat
            if self.frame_i % 2 == 0:
                self.facing *= -1

        elif self.state == "pounce":
            # menyelinap lalu menerkam ke titik kursor yang diincar (usil)
            left, _, right, _ = app_desktop_bounds(self.app)
            top, bottom = self._roam_bounds()
            tx = max(left, min(right - CANVAS_W, self.gaze_x - CANVAS_W // 2))
            ty = max(top, min(bottom, self.gaze_y - CANVAS_H // 2))
            self.facing = 1 if tx > self.x else -1
            self.x = self._step_axis(self.x, tx, POUNCE_SPEED)
            self.y = self._step_axis(self.y, ty, VCHASE_SPEED)
            self.ground_y = self.y
            if self.x == tx and self.y == ty:
                self.show_msg(random.choice(POUNCE_MESSAGES), 3)
                bark(self.app.root, self.app.sound_style)
                self.set_state("jump")

        elif self.state == "jump":
            i = len(JUMP_ARC) - self.state_timer
            i = max(0, min(len(JUMP_ARC) - 1, i))
            self.y = self.ground_y - JUMP_ARC[i]

        # batas layar & kedipan
        left, top, right, bottom = app_desktop_bounds(self.app)
        self.x = max(left, min(right - CANVAS_W, self.x))
        self.y = max(top, min(bottom - CANVAS_H, self.y))
        self._record_motion_facing(previous_x)
        self.blink = (
            self.state in (
                "idle", "dig", "type", "think",
                "curious", "beg",
                "scroll_up", "scroll_down", "meeting_watch",
            )
            and random.random() < 0.08
        )

        # transisi state
        self.state_timer -= 1
        if self.state_timer <= 0:
            if self.state == "type" and typing:
                # Jangan selipkan satu frame idle setiap timer type habis saat
                # pengguna masih aktif mengetik.
                self.state_timer = 20
            elif self.state == "jump":
                self.y = self.ground_y
                self.set_state("happy", 8)
            elif self.state == "eat":
                self.set_state("happy")
            elif self.state == "spin":
                # pusing setelah muter-muter, atau senang saja
                self.set_state("dizzy" if random.random() < 0.35 else "happy",
                               8)
            elif self.state == "pounce":
                # gagal menangkap sampai batas waktu -> nyengir puas saja
                self.set_state("happy", 8)
            elif self.state in (
                "sleep", "happy", "dig", "type",
                "scroll_up", "scroll_down", "meeting_alert", "meeting_watch",
                "dizzy", "curious", "tail_wag", "beg", "glance", "sniff",
                "pee",
            ):
                self.set_state("idle")
            elif self.state not in ("think", "fetch"):
                nxt = random.choices(
                    [
                        "idle", "walk", "sleep", "dig", "curious",
                        "tail_wag", "beg", "zoomies", "spin", "sniff", "pee",
                    ],
                    weights=self.app.state_weights(),
                )[0]
                self.set_state(nxt)
                if nxt == "spin" and random.random() < 0.5:
                    self.show_msg(random.choice(SPIN_MESSAGES), 3)
                elif nxt == "sniff" and random.random() < 0.5:
                    self.show_msg(random.choice(SNIFF_MESSAGES), 3)
                elif nxt == "pee" and random.random() < 0.6:
                    self.show_msg(random.choice(PEE_MESSAGES), 3)

        self.frame_i += 1

    # ------------------------------------------------------------- interaksi
    def _on_press(self, e):
        self._drag_start = (e.x_root, e.y_root, self.x, self.y)
        self._moved = False
        self._pre_drag_state = self.state

    def _on_drag(self, e):
        if not self._drag_start:
            return
        sx, sy, ox, oy = self._drag_start
        dx, dy = e.x_root - sx, e.y_root - sy
        if abs(dx) + abs(dy) > 4 and not self._moved:
            self._moved = True
            self.set_state("hold")
        left, top, right, bottom = app_desktop_bounds(self.app)
        self.x = max(left, min(right - CANVAS_W, ox + dx))
        self.y = max(top, min(bottom - CANVAS_H, oy + dy))
        self.place()

    def _on_release(self, e):
        if not self._moved:
            self.set_state("happy")
            self.app.on_petted()
        else:
            self.ground_y = self.y
            if self._pre_drag_state == "fetch" and self.fetch_bone:
                self.set_state("fetch")
            elif self.app.agent_thinking:
                self.set_state("think")
            else:
                self.set_state("happy", 8)
        self._drag_start = None
        self._pre_drag_state = None

    def _set_theme(self, name):
        self.theme = name
        if self.primary:
            self.app.theme = name
            self.app.save_config()
            if getattr(self.app, "control_center", None):
                self.app.control_center.sync_from_app()

    def _on_menu(self, e):
        app = self.app
        menu = tk.Menu(self.win, tearoff=0)

        menu.add_command(
            label="OPEN CONTROL CENTER",
            command=app.show_control_center,
        )
        menu.add_separator()

        warna = tk.Menu(menu, tearoff=0)
        for name in COLOR_THEMES:
            prefix = "● " if name == self.theme else "   "
            warna.add_command(
                label=prefix + name,
                command=lambda n=name: self._set_theme(n),
            )
        menu.add_cascade(label="🎨  Warna bulu", menu=warna)

        menu.add_command(label="🦴  Beri tulang", command=app.spawn_bone)

        if len(app.pets) < MAX_PETS:
            menu.add_command(label="🐶  Tambah teman", command=app.add_pet)
        if len(app.pets) > 1:
            menu.add_command(
                label="👋  Pulangkan Dogi ini",
                command=lambda: app.remove_pet(self),
            )

        menu.add_separator()
        pomo_label = (
            "🍅  Batalkan Pomodoro" if app.pomo_end
            else f"🍅  Pomodoro {POMODORO_MIN} menit"
        )
        menu.add_command(label=pomo_label, command=app.toggle_pomodoro)
        stretch_label = (
            "🧘  Pengingat peregangan: ON" if app.stretch_on
            else "🧘  Pengingat peregangan: OFF"
        )
        menu.add_command(label=stretch_label, command=app.toggle_stretch)

        update_menu = tk.Menu(menu, tearoff=0)
        update_menu.add_command(
            label="Periksa pembaruan sekarang",
            command=lambda: app.check_updates(manual=True),
        )
        auto_prefix = "● " if app.auto_update else "   "
        update_menu.add_command(
            label=f"{auto_prefix}Pembaruan otomatis",
            command=app.toggle_auto_update,
        )
        channel_menu = tk.Menu(update_menu, tearoff=0)
        for channel, label in (
            ("continuous", "Continuous (setiap push main)"),
            ("stable", "Stable (rilis versi)"),
        ):
            prefix = "● " if app.update_channel == channel else "   "
            channel_menu.add_command(
                label=prefix + label,
                command=lambda value=channel: app.set_update_channel(value),
            )
        update_menu.add_cascade(label="Kanal pembaruan", menu=channel_menu)
        update_menu.add_command(
            label="Buka halaman rilis",
            command=lambda: webbrowser.open(RELEASE_PAGE),
        )
        menu.add_cascade(label="⬆  Pembaruan", menu=update_menu)

        menu.add_separator()
        menu.add_command(
            label="😴  Tidur", command=lambda: self.set_state("sleep")
        )
        menu.add_command(
            label="❤️  Elus", command=lambda: self.set_state("happy")
        )
        behavior_menu = tk.Menu(menu, tearoff=0)
        behavior_menu.add_command(
            label="Zoomies", command=lambda: self.set_state("zoomies")
        )
        behavior_menu.add_command(
            label="Penasaran", command=lambda: self.set_state("curious")
        )
        behavior_menu.add_command(
            label="Goyang ekor", command=lambda: self.set_state("tail_wag")
        )
        behavior_menu.add_command(
            label="Minta perhatian", command=lambda: self.set_state("beg")
        )
        menu.add_cascade(label="Tingkah Dogi", menu=behavior_menu)
        if not HAS_PYNPUT:
            menu.add_command(
                label="(pip install pynput utk reaksi keyboard)",
                state="disabled",
            )
        menu.add_separator()
        menu.add_command(label=f"DogiPet v{VERSION}", state="disabled")
        menu.add_command(label="❌  Keluar semua", command=app.quit)
        menu.tk_popup(e.x_root, e.y_root)

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# -------------------------------------------------------------- control center
class ControlCenter:
    """Jendela pengaturan native yang mengendalikan desktop pet."""

    BG = "#090909"
    PANEL = "#151515"
    PANEL_ALT = "#1e1e1e"
    BORDER = "#383838"
    TEXT = "#f5f2e9"
    MUTED = "#929292"
    ACCENT = "#f2cf45"
    DARK = "#090909"

    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.title("DogiPet Control Center")
        self.win.configure(bg=self.BG)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.hide)
        try:
            self._window_icon = tk.PhotoImage(
                file=str(pathlib.Path(__file__).resolve().parent / "assets" / "dogipet.png")
            )
            self.win.iconphoto(True, self._window_icon)
        except tk.TclError:
            self._window_icon = None

        self.name_var = tk.StringVar(value=app.pet_name)
        self.status_var = tk.StringVar(value="DOGI AKTIF DI DESKTOP")
        self.pomodoro_var = tk.StringVar(value="SIAP UNTUK SESI FOKUS")
        self.theme_var = tk.StringVar(value=app.theme)
        self.note_status_var = tk.StringVar(value="CATATAN TERSIMPAN LOKAL")
        self._current_note_id = None
        self._note_ids = []
        self._loading_note = False
        self._calendar_rendered_ids = ()
        self._hook_state = (0.0, False)  # (kapan dicek, terpasang?)

        self.pages = {}
        self.nav_buttons = {}
        self.theme_buttons = {}
        self._build_shell()
        self._build_home_page()
        self._build_customize_page()
        self._build_focus_page()
        self._build_notes_page()
        self._build_reactions_page()
        self._build_agent_page()
        self._build_updates_page()
        self._build_about_page()
        self.show_page("HOME")
        self.win.update_idletasks()
        natural_width = self.win.winfo_reqwidth()
        natural_height = self.win.winfo_reqheight()
        left, top, right, bottom = app_desktop_bounds(self.app)
        x = max(left + 20, left + (right - left - natural_width) // 2)
        y = max(top + 20, top + (bottom - top - natural_height) // 2)
        self.win.geometry(window_geometry(natural_width, natural_height, x, y))
        self.sync_from_app()
        self.win.withdraw()
        self.win.after(500, self._refresh_loop)

    def _label(self, parent, text="", size=10, color=None, bold=False, **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", parent.cget("bg")),
            fg=color or self.TEXT,
            font=("Consolas", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _button(self, parent, text, command, accent=False, width=24, **kwargs):
        bg = self.ACCENT if accent else self.PANEL_ALT
        fg = self.DARK if accent else self.TEXT
        active_bg = "#ffe474" if accent else "#2b2b2b"
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=self.DARK if accent else self.TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Consolas", 10, "bold"),
            padx=12,
            pady=10,
            **kwargs,
        )

    def _card(self, parent, **kwargs):
        return tk.Frame(
            parent,
            bg=self.PANEL,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            **kwargs,
        )

    def _build_shell(self):
        header = tk.Frame(self.win, bg=self.BG, height=76)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=self.BG)
        brand.pack(side="left", padx=24, pady=14)
        self._label(brand, "DOGIPET", 22, bold=True).pack(anchor="w")
        self._label(
            brand,
            f"TEMAN DESKTOP  /  VERSI {VERSION}",
            8,
            self.MUTED,
        ).pack(anchor="w")

        right = tk.Frame(header, bg=self.BG)
        right.pack(side="right", padx=24, pady=17)
        self._label(
            right,
            textvariable=self.status_var,
            size=9,
            color=self.ACCENT,
            bold=True,
        ).pack(side="left", padx=(0, 18))
        self._button(
            right,
            "SEMBUNYIKAN",
            self.hide,
            width=18,
        ).pack(side="left")

        divider = tk.Frame(self.win, bg=self.BORDER, height=1)
        divider.pack(fill="x")

        body = tk.Frame(self.win, bg=self.BG)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=self.BG, width=196)
        sidebar.pack(side="left", fill="y", padx=(18, 0), pady=18)
        sidebar.pack_propagate(False)

        self._label(sidebar, "PUSAT KONTROL", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=10, pady=(4, 12)
        )
        for page, label in (
            ("HOME", "BERANDA"),
            ("CUSTOMIZE", "TAMPILAN"),
            ("FOCUS", "FOKUS"),
            ("NOTES", "CATATAN & AGENDA"),
            ("REACTIONS", "REAKSI"),
            ("AGENT", "AGENT AI"),
            ("UPDATES", "PEMBARUAN"),
            ("ABOUT", "TENTANG"),
        ):
            button = self._button(
                sidebar,
                label,
                lambda name=page: self.show_page(name),
                width=20,
                anchor="w",
            )
            button.pack(fill="x", pady=3)
            self.nav_buttons[page] = button

        self._label(
            sidebar,
            "KLIK KANAN DOGI UNTUK\nMEMBUKA JENDELA INI LAGI",
            8,
            self.MUTED,
            justify="left",
        ).pack(side="bottom", anchor="w", padx=10, pady=8)

        self.content = tk.Frame(body, bg=self.BG, width=680, height=690)
        self.content.pack(side="left", fill="both", expand=True, padx=18, pady=18)
        self.content.pack_propagate(False)

    def _new_page(self, name, title, subtitle):
        page = tk.Frame(self.content, bg=self.BG)
        self.pages[name] = page
        self._label(page, title, 19, bold=True).pack(anchor="w")
        self._label(page, subtitle, 9, self.MUTED).pack(anchor="w", pady=(2, 16))
        return page

    def _build_home_page(self):
        page = self._new_page(
            "HOME",
            "DOGI SIAP MENEMANIMU.",
            "Teman kecilmu sedang aktif di desktop.",
        )
        columns = tk.Frame(page, bg=self.BG)
        columns.pack(fill="both", expand=True)

        preview_card = self._card(columns, width=360)
        preview_card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        preview_card.pack_propagate(False)
        self._label(preview_card, "PREVIEW LANGSUNG", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 0)
        )
        self.preview = tk.Canvas(
            preview_card,
            width=320,
            height=245,
            bg=self.PANEL,
            highlightthickness=0,
        )
        self.preview.pack(padx=16)
        self.preview_name = self._label(preview_card, self.app.pet_name.upper(), 14, bold=True)
        self.preview_name.pack()
        self._label(
            preview_card,
            "KLIK DAN SERET DI DESKTOP  /  KLIK KANAN UNTUK MENU",
            7,
            self.MUTED,
        ).pack(pady=(5, 12))

        actions = self._card(columns, width=280)
        actions.pack(side="left", fill="y")
        actions.pack_propagate(False)
        self._label(actions, "AKSI CEPAT", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(18, 12)
        )
        for text, command, accent in (
            ("ELUS DOGI", self._pet_primary, True),
            ("BERI TULANG", self.app.spawn_bone, False),
            ("TAMBAH TEMAN", self.app.add_pet, False),
            ("TIDURKAN DOGI", self._sleep_primary, False),
        ):
            self._button(actions, text, command, accent=accent, width=24).pack(
                padx=18, pady=5, fill="x"
            )

        self._label(actions, "KONDISI DOGI", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(14, 6)
        )
        self.stat_bars = {}
        for key, label in (
            ("kenyang", "KENYANG"),
            ("energi", "ENERGI"),
            ("senang", "SENANG"),
        ):
            row = tk.Frame(actions, bg=self.PANEL)
            row.pack(fill="x", padx=18, pady=3)
            self._label(row, label, 7, self.MUTED, width=8, anchor="w").pack(
                side="left"
            )
            bar = tk.Canvas(
                row,
                width=136,
                height=10,
                bg=self.PANEL_ALT,
                highlightthickness=0,
            )
            bar.pack(side="right")
            self.stat_bars[key] = bar

        self.pet_count_label = self._label(actions, "", 8, self.MUTED)
        self.pet_count_label.pack(side="bottom", pady=8)

    def _build_customize_page(self):
        page = self._new_page(
            "CUSTOMIZE",
            "BUAT DOGI JADI MILIKMU.",
            "Pilih nama dan warna bulu yang paling pas.",
        )

        name_card = self._card(page)
        name_card.pack(fill="x", pady=(0, 12))
        self._label(name_card, "NAMA DOGI", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(14, 6)
        )
        name_row = tk.Frame(name_card, bg=self.PANEL)
        name_row.pack(fill="x", padx=18, pady=(0, 16))
        entry = tk.Entry(
            name_row,
            textvariable=self.name_var,
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Consolas", 12, "bold"),
            width=28,
        )
        entry.pack(side="left", ipady=9, padx=(0, 10))
        self._button(name_row, "SIMPAN NAMA", self._save_name, accent=True, width=16).pack(
            side="left"
        )

        theme_card = self._card(page)
        theme_card.pack(fill="x")
        self._label(theme_card, "WARNA BULU", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(14, 4)
        )
        self._label(
            theme_card,
            "Perubahan warna langsung diterapkan ke Dogi utama.",
            8,
            self.MUTED,
        ).pack(anchor="w", padx=18, pady=(0, 12))
        grid = tk.Frame(theme_card, bg=self.PANEL)
        grid.pack(fill="x", padx=14, pady=(0, 14))
        for index, name in enumerate(COLOR_THEMES):
            swatch = COLOR_THEMES[name]["o"]
            button = tk.Button(
                grid,
                text=name.upper(),
                command=lambda value=name: self._select_theme(value),
                bg=self.PANEL_ALT,
                fg=swatch,
                activebackground="#2b2b2b",
                activeforeground=swatch,
                relief="flat",
                bd=0,
                cursor="hand2",
                font=("Consolas", 11, "bold"),
                padx=14,
                pady=8,
                anchor="w",
            )
            button.grid(row=index // 2, column=index % 2, padx=4, pady=3, sticky="ew")
            self.theme_buttons[name] = button
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        sound_card = self._card(page)
        sound_card.pack(fill="x", pady=(12, 0))
        self._label(sound_card, "SUARA GONGGONGAN", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(14, 4)
        )
        self._label(
            sound_card,
            "Pilih gaya suara Dogi; langsung diputar sebagai pratinjau.",
            8,
            self.MUTED,
        ).pack(anchor="w", padx=18, pady=(0, 10))
        sound_row = tk.Frame(sound_card, bg=self.PANEL)
        sound_row.pack(fill="x", padx=14, pady=(0, 14))
        self.sound_buttons = {}
        for style in SOUND_CHOICES:
            button = self._button(
                sound_row,
                style.upper(),
                lambda value=style: self.app.set_sound_style(value),
                width=9,
            )
            button.pack(side="left", padx=4, expand=True, fill="x")
            self.sound_buttons[style] = button

    def _build_focus_page(self):
        page = self._new_page(
            "FOCUS",
            "FOKUS. ISTIRAHAT. ULANGI.",
            "Dogi menjaga waktu fokus dan mengingatkanmu beristirahat.",
        )

        pomo = self._card(page)
        pomo.pack(fill="x", pady=(0, 12))
        self._label(pomo, "TIMER POMODORO", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 4)
        )
        self._label(
            pomo,
            textvariable=self.pomodoro_var,
            size=18,
            color=self.TEXT,
            bold=True,
        ).pack(anchor="w", padx=18, pady=(4, 12))
        self.pomo_button = self._button(
            pomo,
            "MULAI 25 MENIT",
            self.app.toggle_pomodoro,
            accent=True,
            width=24,
        )
        self.pomo_button.pack(anchor="w", padx=18, pady=(0, 18))

        habits = self._card(page)
        habits.pack(fill="both", expand=True)
        self._label(habits, "KEBIASAAN SEHAT", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 10)
        )
        row = tk.Frame(habits, bg=self.PANEL)
        row.pack(fill="x", padx=18, pady=8)
        copy = tk.Frame(row, bg=self.PANEL)
        copy.pack(side="left", fill="x", expand=True)
        self._label(copy, "PENGINGAT PEREGANGAN", 11, bold=True).pack(anchor="w")
        self._label(copy, "Dogi mengingatkanmu setiap 45 menit.", 8, self.MUTED).pack(
            anchor="w", pady=(3, 0)
        )
        self.stretch_button = self._button(
            row,
            "",
            self.app.toggle_stretch,
            width=12,
        )
        self.stretch_button.pack(side="right")

        rest_row = tk.Frame(habits, bg=self.PANEL)
        rest_row.pack(fill="x", padx=18, pady=8)
        rest_copy = tk.Frame(rest_row, bg=self.PANEL)
        rest_copy.pack(side="left", fill="x", expand=True)
        self._label(rest_copy, "AJAK ISTIRAHAT", 11, bold=True).pack(anchor="w")
        self.rest_desc_label = self._label(rest_copy, "", 8, self.MUTED)
        self.rest_desc_label.pack(anchor="w", pady=(3, 0))
        self.rest_button = self._button(
            rest_row,
            "",
            self.app.toggle_rest_reminder,
            width=12,
        )
        self.rest_button.pack(side="right")

        limit_row = tk.Frame(habits, bg=self.PANEL)
        limit_row.pack(fill="x", padx=18, pady=(0, 14))
        self._label(limit_row, "BATAS NONSTOP", 8, self.MUTED, bold=True).pack(
            side="left"
        )
        self.rest_limit_buttons = {}
        for minutes in reversed(REST_CHOICES):
            button = self._button(
                limit_row,
                f"{minutes} MNT",
                lambda value=minutes: self.app.set_rest_after(value),
                width=8,
            )
            button.pack(side="right", padx=3)
            self.rest_limit_buttons[minutes] = button

    def _build_notes_page(self):
        page = self._new_page(
            "NOTES",
            "CATATAN RAPI. AGENDA TERJAGA.",
            "Simpan lokal, rapikan saat diminta, dan biarkan Dogi mengingatkanmu.",
        )

        editor_card = self._card(page, height=390)
        editor_card.pack(fill="x", pady=(0, 10))
        editor_card.pack_propagate(False)
        editor_body = tk.Frame(editor_card, bg=self.PANEL)
        editor_body.pack(fill="both", expand=True, padx=14, pady=14)

        note_sidebar = tk.Frame(editor_body, bg=self.PANEL, width=165)
        note_sidebar.pack(side="left", fill="y", padx=(0, 12))
        note_sidebar.pack_propagate(False)
        self._label(note_sidebar, "DAFTAR CATATAN", 8, self.MUTED, bold=True).pack(
            anchor="w", pady=(0, 6)
        )
        self.note_list = tk.Listbox(
            note_sidebar,
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            selectbackground=self.ACCENT,
            selectforeground=self.DARK,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Consolas", 9),
            exportselection=False,
        )
        self.note_list.pack(fill="both", expand=True)
        self.note_list.bind("<<ListboxSelect>>", self._on_note_select)
        self._button(
            note_sidebar, "+ CATATAN BARU", self._new_note, width=15,
        ).pack(fill="x", pady=(8, 0))

        note_editor = tk.Frame(editor_body, bg=self.PANEL)
        note_editor.pack(side="left", fill="both", expand=True)
        self._label(note_editor, "JUDUL", 8, self.MUTED, bold=True).pack(anchor="w")
        self.note_title = tk.Entry(
            note_editor,
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Consolas", 11, "bold"),
        )
        self.note_title.pack(fill="x", ipady=6, pady=(4, 8))
        self.note_body = tk.Text(
            note_editor,
            height=12,
            wrap="word",
            undo=True,
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            selectbackground="#635a2a",
            relief="flat",
            padx=10,
            pady=8,
            font=("Consolas", 9),
        )
        self.note_body.pack(fill="both", expand=True)

        note_actions = tk.Frame(note_editor, bg=self.PANEL)
        note_actions.pack(fill="x", pady=(8, 0))
        self._button(
            note_actions, "SIMPAN", self._save_note, accent=True, width=10,
        ).pack(side="left", padx=(0, 5))
        self._button(
            note_actions, "HAPUS", self._delete_note, width=9,
        ).pack(side="left", padx=(0, 5))
        self._button(
            note_actions, "ATUR AI", self._configure_ai, width=9,
        ).pack(side="left", padx=(0, 5))
        self.ai_note_button = self._button(
            note_actions, "RAPIKAN AI", self._organize_current_note, width=13,
        )
        self.ai_note_button.pack(side="right")
        self._label(
            note_editor,
            textvariable=self.note_status_var,
            size=7,
            color=self.MUTED,
        ).pack(anchor="w", pady=(5, 0))

        calendar_card = self._card(page)
        calendar_card.pack(fill="both", expand=True)
        calendar_header = tk.Frame(calendar_card, bg=self.PANEL)
        calendar_header.pack(fill="x", padx=14, pady=(12, 6))
        self._label(
            calendar_header, "GOOGLE CALENDAR", 8, self.MUTED, bold=True
        ).pack(side="left")
        self.calendar_status_label = self._label(
            calendar_header, "", 8, self.ACCENT, bold=True
        )
        self.calendar_status_label.pack(side="right")

        calendar_body = tk.Frame(calendar_card, bg=self.PANEL)
        calendar_body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.calendar_list = tk.Listbox(
            calendar_body,
            height=6,
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            selectbackground="#635a2a",
            selectforeground=self.TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Consolas", 8),
            exportselection=False,
        )
        self.calendar_list.pack(side="left", fill="both", expand=True)
        self.calendar_list.bind("<Double-Button-1>", self._open_calendar_event)
        calendar_actions = tk.Frame(calendar_body, bg=self.PANEL)
        calendar_actions.pack(side="left", fill="y", padx=(10, 0))
        self._button(
            calendar_actions, "HUBUNGKAN", self._connect_google_calendar, width=12,
        ).pack(fill="x", pady=(0, 4))
        self._button(
            calendar_actions, "SINKRON", self._sync_google_calendar, width=12,
        ).pack(fill="x", pady=4)
        self._button(
            calendar_actions, "PUTUSKAN", self._disconnect_google_calendar, width=12,
        ).pack(fill="x", pady=4)

        self._refresh_notes(create_if_empty=True)

    def _build_agent_page(self):
        page = self._new_page(
            "AGENT",
            "DOGI IKUT MENGAWAL AGENT-MU.",
            "Muka mikir saat agent bekerja, perayaan saat tugas selesai.",
        )

        setup = self._card(page)
        setup.pack(fill="x", pady=(0, 12))
        self._label(setup, "INTEGRASI CLAUDE CODE", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 4)
        )
        self.hook_status_label = self._label(setup, "", 15, bold=True)
        self.hook_status_label.pack(anchor="w", padx=18)
        self._label(
            setup,
            f"Hook ditulis ke {agent_hooks.SETTINGS_FILE}",
            8,
            self.MUTED,
        ).pack(anchor="w", padx=18, pady=(4, 0))
        self.hook_button = self._button(
            setup,
            "PASANG HOOK",
            self._toggle_claude_hook,
            accent=True,
            width=24,
        )
        self.hook_button.pack(anchor="w", padx=18, pady=(12, 18))

        info = self._card(page)
        info.pack(fill="both", expand=True)
        self._label(info, "CARA KERJA", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 8)
        )
        self._label(
            info,
            "Claude Code memanggil DogiPet saat kamu mengirim prompt (thinking)\n"
            "dan saat agent selesai menjawab (done). Status hanya ditulis lokal ke\n"
            "~/.dogi/agent_status.json — tanpa mengirim data ke mana pun.",
            9,
            self.TEXT,
            justify="left",
        ).pack(anchor="w", padx=18)
        self._label(
            info,
            "AGENT LAIN? PANGGIL:  python dogi_hook.py thinking|done",
            8,
            self.MUTED,
        ).pack(anchor="w", padx=18, pady=(12, 0))
        self._button(
            info,
            "UJI PERAYAAN",
            lambda: self.app.celebrate_all("Guk guk! Tugas selesai!"),
            width=24,
        ).pack(anchor="w", padx=18, pady=(14, 18))

    def _build_reactions_page(self):
        page = self._new_page(
            "REACTIONS",
            "DOGI PEKA DENGAN AKTIVITASMU.",
            "Scroll dan meeting memunculkan gerakan kontekstual yang berbeda.",
        )

        scroll_card = self._card(page)
        scroll_card.pack(fill="x", pady=(0, 12))
        scroll_row = tk.Frame(scroll_card, bg=self.PANEL)
        scroll_row.pack(fill="x", padx=18, pady=18)
        scroll_copy = tk.Frame(scroll_row, bg=self.PANEL)
        scroll_copy.pack(side="left", fill="x", expand=True)
        self._label(scroll_copy, "IKUT SCROLL", 11, bold=True).pack(anchor="w")
        self._label(
            scroll_copy,
            "Dogi menggerakkan indikator laptop mengikuti scroll atas/bawah.",
            8,
            self.MUTED,
        ).pack(anchor="w", pady=(3, 0))
        self.scroll_reaction_button = self._button(
            scroll_row,
            "",
            self.app.toggle_scroll_reaction,
            width=12,
        )
        self.scroll_reaction_button.pack(side="right")

        meeting_card = self._card(page)
        meeting_card.pack(fill="x", pady=(0, 12))
        self._label(meeting_card, "REAKSI VIDEO MEETING", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 4)
        )
        self.meeting_status_label = self._label(meeting_card, "", 14, bold=True)
        self.meeting_status_label.pack(anchor="w", padx=18, pady=(4, 14))

        meeting_row = tk.Frame(meeting_card, bg=self.PANEL)
        meeting_row.pack(fill="x", padx=18, pady=6)
        meeting_copy = tk.Frame(meeting_row, bg=self.PANEL)
        meeting_copy.pack(side="left", fill="x", expand=True)
        self._label(meeting_copy, "LIHAT JENDELA MEETING", 10, bold=True).pack(anchor="w")
        self._label(
            meeting_copy,
            "Zoom, Teams, Meet, Webex, Slack/Discord call.",
            8,
            self.MUTED,
        ).pack(anchor="w")
        self.meeting_reaction_button = self._button(
            meeting_row,
            "",
            self.app.toggle_meeting_reaction,
            width=12,
        )
        self.meeting_reaction_button.pack(side="right")

        bark_row = tk.Frame(meeting_card, bg=self.PANEL)
        bark_row.pack(fill="x", padx=18, pady=6)
        bark_copy = tk.Frame(bark_row, bg=self.PANEL)
        bark_copy.pack(side="left", fill="x", expand=True)
        self._label(bark_copy, "GONGGONG SAAT MEETING MULAI", 10, bold=True).pack(
            anchor="w"
        )
        self._label(
            bark_copy,
            "Sekali saat jendela meeting baru terdeteksi, bukan berulang.",
            8,
            self.MUTED,
        ).pack(anchor="w")
        self.meeting_bark_button = self._button(
            bark_row,
            "",
            self.app.toggle_meeting_bark,
            width=12,
        )
        self.meeting_bark_button.pack(side="right")

        self._label(
            meeting_card,
            "PRIVASI: DOGIPET HANYA MEMBACA NAMA APP, JUDUL, DAN POSISI\n"
            "JENDELA. TIDAK MENGAKSES KAMERA, MIKROFON, ATAU ISI MEETING.",
            8,
            self.MUTED,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(18, 16))

        system_card = self._card(page)
        system_card.pack(fill="x")
        self._label(system_card, "SISTEM", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 8)
        )

        startup_row = tk.Frame(system_card, bg=self.PANEL)
        startup_row.pack(fill="x", padx=18, pady=6)
        startup_copy = tk.Frame(startup_row, bg=self.PANEL)
        startup_copy.pack(side="left", fill="x", expand=True)
        self._label(startup_copy, "JALAN SAAT WINDOWS NYALA", 10, bold=True).pack(
            anchor="w"
        )
        self._label(
            startup_copy,
            "Dogi otomatis muncul setiap kali kamu login.",
            8,
            self.MUTED,
        ).pack(anchor="w")
        self.startup_button = self._button(
            startup_row, "", self.app.toggle_startup, width=12,
        )
        self.startup_button.pack(side="right")

        presentation_row = tk.Frame(system_card, bg=self.PANEL)
        presentation_row.pack(fill="x", padx=18, pady=(6, 16))
        presentation_copy = tk.Frame(presentation_row, bg=self.PANEL)
        presentation_copy.pack(side="left", fill="x", expand=True)
        self._label(
            presentation_copy, "MODE PRESENTASI (JANGAN GANGGU)", 10, bold=True
        ).pack(anchor="w")
        self._label(
            presentation_copy,
            "Sembunyi otomatis saat ada aplikasi fullscreen / berbagi layar.",
            8,
            self.MUTED,
        ).pack(anchor="w")
        self.presentation_button = self._button(
            presentation_row, "", self.app.toggle_presentation_hide, width=12,
        )
        self.presentation_button.pack(side="right")

    def _build_updates_page(self):
        page = self._new_page(
            "UPDATES",
            "DOGI SELALU TERBARU.",
            "Pembaruan dikirim langsung dari GitHub Releases milikmu.",
        )

        current = self._card(page)
        current.pack(fill="x", pady=(0, 12))
        current_left = tk.Frame(current, bg=self.PANEL)
        current_left.pack(side="left", padx=18, pady=16)
        self._label(current_left, "VERSI TERPASANG", 8, self.MUTED, bold=True).pack(
            anchor="w"
        )
        build_label = BUILD_ID[:8] if BUILD_ID != "source" else "LOCAL SOURCE"
        self._label(current_left, f"{VERSION}  /  {build_label}", 16, bold=True).pack(
            anchor="w", pady=(4, 0)
        )
        self._button(
            current,
            "PERIKSA SEKARANG",
            lambda: self.app.check_updates(manual=True),
            accent=True,
            width=16,
        ).pack(side="right", padx=18)

        settings = self._card(page)
        settings.pack(fill="both", expand=True)
        self._label(settings, "PENGATURAN PEMBARUAN", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(16, 12)
        )

        auto_row = tk.Frame(settings, bg=self.PANEL)
        auto_row.pack(fill="x", padx=18, pady=6)
        auto_copy = tk.Frame(auto_row, bg=self.PANEL)
        auto_copy.pack(side="left", fill="x", expand=True)
        self._label(auto_copy, "PEMERIKSAAN OTOMATIS", 10, bold=True).pack(anchor="w")
        self._label(auto_copy, "Periksa diam-diam setelah DogiPet dimulai.", 8, self.MUTED).pack(
            anchor="w"
        )
        self.auto_button = self._button(
            auto_row,
            "",
            self.app.toggle_auto_update,
            width=12,
        )
        self.auto_button.pack(side="right")

        self._label(settings, "KANAL PEMBARUAN", 8, self.MUTED, bold=True).pack(
            anchor="w", padx=18, pady=(22, 8)
        )
        channel_row = tk.Frame(settings, bg=self.PANEL)
        channel_row.pack(fill="x", padx=18)
        self.continuous_button = self._button(
            channel_row,
            "CONTINUOUS",
            lambda: self.app.set_update_channel("continuous"),
            width=18,
        )
        self.continuous_button.pack(side="left", padx=(0, 8))
        self.stable_button = self._button(
            channel_row,
            "STABLE",
            lambda: self.app.set_update_channel("stable"),
            width=18,
        )
        self.stable_button.pack(side="left")
        self._label(
            settings,
            "CONTINUOUS mengikuti setiap push ke main. STABLE mengikuti tag versi.",
            8,
            self.MUTED,
        ).pack(anchor="w", padx=18, pady=(8, 0))

    def _build_about_page(self):
        page = self._new_page(
            "ABOUT",
            "ANJING KECIL DENGAN TUGAS BESAR.",
            "Dibangun sebagai aplikasi teman desktop Windows sungguhan.",
        )
        card = self._card(page)
        card.pack(fill="both", expand=True)
        self._label(card, "DOGIPET", 26, bold=True).pack(anchor="w", padx=24, pady=(26, 4))
        self._label(card, f"VERSI {VERSION}", 9, self.ACCENT, bold=True).pack(
            anchor="w", padx=24
        )
        self._label(
            card,
            "Anjing piksel yang mengikuti kursor, bereaksi saat kamu mengetik,\n"
            "merapikan catatan, mengingatkan agenda, dan merayakan tugas AI.",
            10,
            self.TEXT,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(22, 18))
        self._label(
            card,
            "TANPA PELACAKAN  /  INTEGRASI OPT-IN  /  UPDATE GITHUB",
            8,
            self.MUTED,
            bold=True,
        ).pack(anchor="w", padx=24)
        self._button(
            card,
            "BUKA GITHUB",
            lambda: webbrowser.open("https://github.com/1oneGod1/DogiPet"),
            accent=True,
            width=18,
        ).pack(anchor="w", padx=24, pady=28)

    def show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        for page_name, button in self.nav_buttons.items():
            active = page_name == name
            button.configure(
                bg=self.ACCENT if active else self.PANEL_ALT,
                fg=self.DARK if active else self.TEXT,
                activebackground="#ffe474" if active else "#2b2b2b",
            )

    def _draw_preview(self):
        self.preview.delete("all")
        pet = self.app.pets[0] if self.app.pets else None
        state = pet.state if pet else "idle"
        asset_state = sprite_asset_state(state)
        if asset_state not in SPRITE_FRAME_COUNTS:
            asset_state = "idle"
        frame_index = sprite_frame_index(asset_state, pet.frame_i) if pet else 0
        mirrored = bool(pet and sprite_is_mirrored(asset_state, pet.visual_facing()))
        suffix = "_left" if mirrored else ""
        path = resource_path(
            "assets", "sprites", self.app.theme.lower(),
            f"{asset_state}_{frame_index}{suffix}.png",
        )
        try:
            self._preview_sprite_image = tk.PhotoImage(file=str(path))
        except tk.TclError:
            self._preview_sprite_image = None
        if self._preview_sprite_image is not None:
            self.preview.create_image(
                int(self.preview.cget("width")) // 2,
                int(self.preview.cget("height")) // 2,
                image=self._preview_sprite_image,
            )
            return
        frame = IDLE_1
        scale = 13
        width = len(frame[0]) * scale
        height = len(frame) * scale
        ox = (int(self.preview.cget("width")) - width) // 2
        oy = (int(self.preview.cget("height")) - height) // 2
        palette = dict(FIXED_COLORS)
        palette.update(COLOR_THEMES[self.app.theme])
        for y, row in enumerate(frame):
            for x, key in enumerate(row):
                color = palette.get(key)
                if color:
                    self.preview.create_rectangle(
                        ox + x * scale,
                        oy + y * scale,
                        ox + (x + 1) * scale,
                        oy + (y + 1) * scale,
                        fill=color,
                        outline=color,
                    )

    # ----------------------------------------------------- catatan & agenda
    def _refresh_notes(self, select_id=None, create_if_empty=False):
        try:
            notes = self.app.note_store.all()
            if create_if_empty and not notes:
                notes = [self.app.note_store.create()]
        except Exception as exc:
            messagebox.showerror("Catatan DogiPet", str(exc), parent=self.win)
            return
        self._loading_note = True
        try:
            self.note_list.delete(0, "end")
            self._note_ids = [note.id for note in notes]
            for note in notes:
                self.note_list.insert("end", note.title)
            wanted = select_id or self._current_note_id
            if wanted not in self._note_ids and self._note_ids:
                wanted = self._note_ids[0]
            if wanted in self._note_ids:
                index = self._note_ids.index(wanted)
                self.note_list.selection_set(index)
                self.note_list.see(index)
                self._load_note(wanted)
        finally:
            self._loading_note = False

    def _load_note(self, note_id):
        note = self.app.note_store.get(note_id)
        if not note:
            return
        self._current_note_id = note.id
        self.note_title.delete(0, "end")
        self.note_title.insert(0, note.title)
        self.note_body.delete("1.0", "end")
        self.note_body.insert("1.0", note.body)
        self.note_status_var.set("CATATAN TERSIMPAN LOKAL")

    def _persist_current_note(self):
        if not self._current_note_id:
            return None
        title = self.note_title.get()
        body = self.note_body.get("1.0", "end-1c")
        return self.app.note_store.update(self._current_note_id, title, body)

    def _on_note_select(self, _event=None):
        if self._loading_note:
            return
        selection = self.note_list.curselection()
        if not selection:
            return
        note_id = self._note_ids[selection[0]]
        if note_id == self._current_note_id:
            return
        try:
            self._persist_current_note()
            self._load_note(note_id)
        except Exception as exc:
            messagebox.showerror("Catatan DogiPet", str(exc), parent=self.win)

    def _new_note(self):
        try:
            self._persist_current_note()
            note = self.app.note_store.create()
            self._refresh_notes(select_id=note.id)
            self.note_title.focus_set()
            self.note_title.selection_range(0, "end")
        except Exception as exc:
            messagebox.showerror("Catatan DogiPet", str(exc), parent=self.win)

    def _save_note(self):
        try:
            note = self._persist_current_note()
            if note:
                self._refresh_notes(select_id=note.id)
                self.note_status_var.set("TERSIMPAN  /  HANYA DI KOMPUTER INI")
                if self.app.pets:
                    self.app.pets[0].show_msg("Catatan tersimpan!", 3)
        except Exception as exc:
            messagebox.showerror("Catatan DogiPet", str(exc), parent=self.win)

    def _delete_note(self):
        if not self._current_note_id:
            return
        if not messagebox.askyesno(
            "Hapus catatan", "Hapus catatan ini secara permanen?", parent=self.win
        ):
            return
        try:
            self.app.note_store.delete(self._current_note_id)
            self._current_note_id = None
            self._refresh_notes(create_if_empty=True)
        except Exception as exc:
            messagebox.showerror("Catatan DogiPet", str(exc), parent=self.win)

    def _configure_ai(self):
        configured = self.app.has_openai_key()
        prompt = (
            "Masukkan API key OpenAI baru. Key disimpan terenkripsi dengan "
            "Windows DPAPI dan hanya dipakai saat tombol Rapikan AI ditekan."
        )
        if configured:
            prompt += "\n\nKosongkan untuk menghapus key yang tersimpan."
        key = simpledialog.askstring(
            "Atur AI Catatan", prompt, parent=self.win, show="*"
        )
        if key is None:
            return False
        try:
            self.app.set_openai_key(key)
        except SecureStoreError as exc:
            messagebox.showerror("Atur AI Catatan", str(exc), parent=self.win)
            return False
        if key.strip():
            self.note_status_var.set(f"AI SIAP  /  {self.app.ai_model}")
            return True
        self.note_status_var.set("API KEY AI DIHAPUS")
        return False

    def _organize_current_note(self):
        text = self.note_body.get("1.0", "end-1c")
        if not self.app.has_openai_key() and not self._configure_ai():
            return
        self.ai_note_button.configure(state="disabled")
        self.note_status_var.set("AI SEDANG MERAPIKAN CATATAN...")

        def finished(result, error):
            self.ai_note_button.configure(state="normal")
            if error:
                self.note_status_var.set("AI GAGAL  /  CATATAN TIDAK DIUBAH")
                messagebox.showwarning("Rapikan dengan AI", error, parent=self.win)
                return
            self.note_body.delete("1.0", "end")
            self.note_body.insert("1.0", result)
            try:
                note = self._persist_current_note()
                if note:
                    self._refresh_notes(select_id=note.id)
            except Exception as exc:
                messagebox.showwarning("Simpan catatan", str(exc), parent=self.win)
            self.note_status_var.set("AI SELESAI  /  HASIL SUDAH TERSIMPAN")
            if self.app.pets:
                self.app.pets[0].set_state("happy")
                self.app.pets[0].show_msg("Catatan sudah rapi!", 4)

        self.app.organize_note_async(text, finished)

    def _connect_google_calendar(self):
        try:
            has_client = bool(
                self.app.secure_store.get("google_calendar_client", {})
            )
        except SecureStoreError as exc:
            messagebox.showerror("Google Calendar", str(exc), parent=self.win)
            return
        credentials = None
        if not has_client:
            credentials = filedialog.askopenfilename(
                parent=self.win,
                title="Pilih OAuth Client JSON (Desktop app)",
                filetypes=(("Google OAuth JSON", "*.json"), ("Semua file", "*.*")),
            )
            if not credentials:
                return
        self.calendar_status_label.configure(text="BUKA BROWSER UNTUK LOGIN")

        def finished(success, error):
            if not success:
                messagebox.showwarning("Google Calendar", error, parent=self.win)
            self.sync_from_app()

        if self.app.connect_google_calendar_async(credentials, finished):
            if self.app.pets:
                self.app.pets[0].show_msg("Login Google di browser ya!", 7)

    def _sync_google_calendar(self):
        def finished(success, error):
            if not success and error:
                messagebox.showwarning("Google Calendar", error, parent=self.win)
            self.sync_from_app()

        self.app.sync_google_calendar_async(manual=True, callback=finished)

    def _disconnect_google_calendar(self):
        if not messagebox.askyesno(
            "Putuskan Google Calendar",
            "Hapus token akun Google dari komputer ini?",
            parent=self.win,
        ):
            return
        try:
            self.app.disconnect_google_calendar()
            self._calendar_rendered_ids = ()
            self.sync_from_app()
        except CalendarIntegrationError as exc:
            messagebox.showerror("Google Calendar", str(exc), parent=self.win)

    def _refresh_calendar_events(self):
        signature = tuple(
            (event.id, event.title, event.start.isoformat())
            for event in self.app.calendar_events
        )
        if signature == self._calendar_rendered_ids:
            return
        self._calendar_rendered_ids = signature
        self.calendar_list.delete(0, "end")
        if not self.app.calendar_events:
            self.calendar_list.insert("end", "Belum ada agenda untuk 7 hari ke depan.")
            return
        for event in self.app.calendar_events:
            self.calendar_list.insert("end", event.display())

    def _open_calendar_event(self, _event=None):
        selection = self.calendar_list.curselection()
        if not selection or selection[0] >= len(self.app.calendar_events):
            return
        link = self.app.calendar_events[selection[0]].html_link
        if link:
            webbrowser.open(link)

    def _pet_primary(self):
        if self.app.pets:
            self.app.pets[0].set_state("happy")
            self.app.pets[0].show_msg("Senang!", 2)
            self.app.on_petted()

    def _toggle_claude_hook(self):
        try:
            if agent_hooks.is_installed():
                agent_hooks.uninstall()
                message = "Hook Claude Code dilepas."
            else:
                agent_hooks.install()
                message = (
                    "Hook terpasang! Kirim prompt di Claude Code dan lihat "
                    "Dogi ikut berpikir."
                )
        except agent_hooks.HookError as exc:
            messagebox.showerror("Integrasi Claude Code", str(exc))
            return
        self._hook_state = (0.0, False)  # paksa pengecekan ulang
        self.sync_from_app()
        messagebox.showinfo("Integrasi Claude Code", message)

    def _sleep_primary(self):
        if self.app.pets:
            self.app.pets[0].set_state("sleep")

    def _save_name(self):
        name = self.name_var.get().strip()[:24] or "Dogi"
        self.app.pet_name = name
        self.name_var.set(name)
        self.app.save_config()
        self.preview_name.configure(text=name.upper())
        if self.app.pets:
            self.app.pets[0].show_msg(f"Namaku {name}!", 3)

    def _select_theme(self, name):
        if not self.app.pets:
            return
        self.app.theme = name
        self.app.pets[0]._set_theme(name)
        self.theme_var.set(name)
        self.sync_from_app()

    def sync_from_app(self):
        self.preview_name.configure(text=self.app.pet_name.upper())
        self._draw_preview()
        self.pet_count_label.configure(text=f"{len(self.app.pets)} / {MAX_PETS} DOGI AKTIF")
        for name, button in self.theme_buttons.items():
            selected = name == self.app.theme
            button.configure(
                bg=self.ACCENT if selected else self.PANEL_ALT,
                fg=self.DARK if selected else COLOR_THEMES[name]["o"],
            )
        self.stretch_button.configure(
            text="ON" if self.app.stretch_on else "OFF",
            bg=self.ACCENT if self.app.stretch_on else self.PANEL_ALT,
            fg=self.DARK if self.app.stretch_on else self.TEXT,
        )
        self.auto_button.configure(
            text="ON" if self.app.auto_update else "OFF",
            bg=self.ACCENT if self.app.auto_update else self.PANEL_ALT,
            fg=self.DARK if self.app.auto_update else self.TEXT,
        )
        continuous = self.app.update_channel == "continuous"
        self.continuous_button.configure(
            bg=self.ACCENT if continuous else self.PANEL_ALT,
            fg=self.DARK if continuous else self.TEXT,
        )
        self.stable_button.configure(
            bg=self.ACCENT if not continuous else self.PANEL_ALT,
            fg=self.DARK if not continuous else self.TEXT,
        )

        self.scroll_reaction_button.configure(
            text="ON" if self.app.scroll_reaction_on else "OFF",
            bg=self.ACCENT if self.app.scroll_reaction_on else self.PANEL_ALT,
            fg=self.DARK if self.app.scroll_reaction_on else self.TEXT,
        )
        self.meeting_reaction_button.configure(
            text="ON" if self.app.meeting_reaction_on else "OFF",
            bg=self.ACCENT if self.app.meeting_reaction_on else self.PANEL_ALT,
            fg=self.DARK if self.app.meeting_reaction_on else self.TEXT,
        )
        meeting_bark_enabled = (
            self.app.meeting_reaction_on and self.app.meeting_bark_on
        )
        self.meeting_bark_button.configure(
            text="ON" if self.app.meeting_bark_on else "OFF",
            state="normal" if self.app.meeting_reaction_on else "disabled",
            bg=self.ACCENT if meeting_bark_enabled else self.PANEL_ALT,
            fg=self.DARK if meeting_bark_enabled else self.TEXT,
        )
        startup_supported = startup_registry.is_supported()
        self.startup_button.configure(
            text=("ON" if self.app.startup_on else "OFF")
            if startup_supported else "N/A",
            state="normal" if startup_supported else "disabled",
            bg=self.ACCENT if self.app.startup_on else self.PANEL_ALT,
            fg=self.DARK if self.app.startup_on else self.TEXT,
        )
        self.presentation_button.configure(
            text="ON" if self.app.presentation_hide_on else "OFF",
            bg=self.ACCENT if self.app.presentation_hide_on else self.PANEL_ALT,
            fg=self.DARK if self.app.presentation_hide_on else self.TEXT,
        )
        if self.app.meeting_active:
            meeting_status = f"MEETING TERDETEKSI  /  {self.app.meeting_title.upper()}"
        else:
            meeting_status = "TIDAK ADA MEETING AKTIF"
        self.meeting_status_label.configure(
            text=meeting_status,
            fg=self.ACCENT if self.app.meeting_active else self.TEXT,
        )

        for style, button in self.sound_buttons.items():
            selected = style == self.app.sound_style
            button.configure(
                bg=self.ACCENT if selected else self.PANEL_ALT,
                fg=self.DARK if selected else self.TEXT,
            )
        self.rest_button.configure(
            text="ON" if self.app.rest_reminder_on else "OFF",
            bg=self.ACCENT if self.app.rest_reminder_on else self.PANEL_ALT,
            fg=self.DARK if self.app.rest_reminder_on else self.TEXT,
        )
        self.rest_desc_label.configure(
            text=(
                f"Dogi mengajakmu rehat setelah {self.app.rest_after_min} "
                "menit aktif nonstop."
            )
        )
        for minutes, button in self.rest_limit_buttons.items():
            selected = minutes == self.app.rest_after_min
            button.configure(
                bg=self.ACCENT if selected else self.PANEL_ALT,
                fg=self.DARK if selected else self.TEXT,
            )

        self.calendar_status_label.configure(
            text=self.app.calendar_status,
            fg=(
                self.ACCENT
                if "TERHUBUNG" in self.app.calendar_status
                and "BELUM" not in self.app.calendar_status
                else self.TEXT
            ),
        )
        self._refresh_calendar_events()

        for key, bar in self.stat_bars.items():
            value = self.app.stats.get(key, 0)
            width = int(int(bar.cget("width")) * value / STAT_MAX)
            color = self.ACCENT if value >= NEED_LOW else "#e2574c"
            bar.delete("all")
            if width > 0:
                bar.create_rectangle(
                    0, 0, width, int(bar.cget("height")),
                    fill=color, outline=color,
                )

        checked_at, installed = self._hook_state
        if time.time() - checked_at > 5:
            installed = agent_hooks.is_installed()
            self._hook_state = (time.time(), installed)
        self.hook_status_label.configure(
            text="HOOK TERPASANG" if installed else "HOOK BELUM TERPASANG",
            fg=self.ACCENT if installed else self.TEXT,
        )
        self.hook_button.configure(
            text="LEPAS HOOK" if installed else "PASANG HOOK",
            bg=self.PANEL_ALT if installed else self.ACCENT,
            fg=self.TEXT if installed else self.DARK,
        )

    def _refresh_loop(self):
        try:
            if self.app.pomo_end:
                remaining = max(0, int(self.app.pomo_end - time.time()))
                self.pomodoro_var.set(f"TERSISA {remaining // 60:02d}:{remaining % 60:02d}")
                self.pomo_button.configure(text="BATALKAN TIMER", bg=self.PANEL_ALT, fg=self.TEXT)
            else:
                self.pomodoro_var.set("SIAP UNTUK SESI FOKUS")
                self.pomo_button.configure(text="MULAI 25 MENIT", bg=self.ACCENT, fg=self.DARK)
            self.pet_count_label.configure(text=f"{len(self.app.pets)} / {MAX_PETS} DOGI AKTIF")
            self.sync_from_app()
            self.win.after(750, self._refresh_loop)
        except tk.TclError:
            return

    def show(self):
        self.sync_from_app()
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

    def hide(self):
        self.win.withdraw()


# ------------------------------------------------------------- aplikasi utama
class DogiApp:
    def __init__(self, smoke_test=False, opaque_preview=False):
        self.smoke_test = smoke_test
        self.root = tk.Tk()
        self.root.withdraw()  # root disembunyikan; tiap Dogi punya jendela

        self.transparent_ok = False
        if sys.platform.startswith("win") and not opaque_preview:
            probe = tk.Toplevel(self.root)
            try:
                probe.attributes("-transparentcolor", TRANSPARENT)
                self.transparent_ok = True
            except tk.TclError:
                pass
            probe.destroy()

        (
            self.screen_left,
            self.screen_top,
            self.screen_right,
            self.screen_bottom,
        ) = virtual_desktop_bounds(self.root)
        self.screen_w = self.screen_right - self.screen_left
        self.screen_h = self.screen_bottom - self.screen_top

        # fitur bersama
        self.pomo_end = None
        self.stretch_on = True
        self.last_stretch = time.time()
        self.agent_thinking = False
        self._status_mtime = 0
        self._last_done_ts = 0
        self._thinking_since = 0.0
        # status lama tidak dirayakan ulang setiap aplikasi dibuka; status
        # "thinking" yang sudah basi (mis. sesi lama/crash) juga diabaikan agar
        # Dogi tidak langsung membeku saat aplikasi baru dibuka.
        try:
            stale = json.loads(STATUS_FILE.read_text())
            self._status_mtime = STATUS_FILE.stat().st_mtime
            self._last_done_ts = float(stale.get("ts") or 0)
            fresh = (time.time() - self._last_done_ts) < THINK_STARTUP_FRESH_S
            self.agent_thinking = stale.get("status") == "thinking" and fresh
            if self.agent_thinking:
                self._thinking_since = self._last_done_ts
        except Exception:
            pass
        self.last_key_time = 0
        self.last_scroll_time = 0
        self.scroll_direction = 0
        self.last_cursor = (0, 0)
        self.cursor_swing = CursorSwingDetector()
        self._friend_cd = 0

        self.auto_update = True
        self.update_channel = "continuous"
        self.update_manager = UpdateManager()
        self._installer_pending = None
        self.pet_name = "Dogi"
        self.show_control_center_on_start = True
        self.control_center = None

        # Catatan tersimpan lokal; API key dan token OAuth berada dalam blob
        # DPAPI terpisah, tidak pernah masuk config.json atau notes.json.
        self.ai_model = DEFAULT_AI_MODEL
        self.note_store = NotesStore(NOTES_FILE)
        self.secure_store = SecureStore(CREDENTIALS_FILE)
        self.calendar_integration = GoogleCalendarIntegration(self.secure_store)
        self.calendar_events = []
        self.calendar_connected = False
        self.calendar_status = "GOOGLE CALENDAR BELUM TERHUBUNG"
        self.calendar_reminder_min = DEFAULT_CALENDAR_REMINDER_MIN
        self._calendar_sync_at = 0.0
        self._calendar_syncing = False
        self._calendar_reminded = set()

        self.stats = dict(DEFAULT_STATS)
        self._last_stats_tick = time.time()
        self._stats_saved = time.time()
        self._nag_cd = 0.0
        self._clock_cd = 0.0
        self._mischief_at = time.time() + random.uniform(
            MISCHIEF_MIN_GAP, MISCHIEF_MAX_GAP
        )
        self.last_greet_date = ""
        self.last_lunch_date = ""

        self.sound_style = DEFAULT_SOUND
        self.rest_reminder_on = True
        self.rest_after_min = 60
        self.activity = ActivityMonitor()
        self._rest_nag_at = 0.0
        self._rest_exceeded = False

        self.scroll_reaction_on = True
        self.meeting_reaction_on = True
        self.meeting_bark_on = True
        self.presentation_hide_on = True
        self._presentation_checked = 0.0
        self._hidden_for_presentation = False
        self.startup_on = startup_registry.is_enabled()
        self.meeting_active = False
        self.meeting_title = ""
        self._meeting_key = None
        self._meeting_poll_at = 0.0
        self._meeting_last_seen = 0.0
        self._meeting_watch_at = 0.0

        self.theme = "Shiba"
        self._load_config()
        try:
            if self.calendar_integration.connected():
                self.calendar_connected = True
                self.calendar_status = "GOOGLE CALENDAR TERHUBUNG"
        except SecureStoreError:
            self.calendar_status = "KREDENSIAL WINDOWS TIDAK DAPAT DIBUKA"
        ensure_bark_wav(self.sound_style)

        if HAS_PYNPUT and not self.smoke_test:
            listener = _pynput_keyboard.Listener(on_press=self._on_key)
            listener.daemon = True
            listener.start()
            mouse_listener = _pynput_mouse.Listener(on_scroll=self._on_scroll)
            mouse_listener.daemon = True
            mouse_listener.start()

        self.pets = [
            DogiPet(
                self, self.screen_left + (self.screen_w - CANVAS_W) // 2,
                self.theme, primary=True,
            )
        ]
        self.bones = []
        self.control_center = ControlCenter(self)

        self.root.after(TICK_MS, self._tick)
        if self.show_control_center_on_start and not self.smoke_test:
            self.root.after(250, self.show_control_center)
        if self.auto_update and getattr(sys, "frozen", False):
            self.root.after(3500, self.check_updates)

    # ------------------------------------------------------------- konfigurasi
    def _load_config(self):
        try:
            cfg = json.loads(CONF_FILE.read_text())
            if cfg.get("theme") in COLOR_THEMES:
                self.theme = cfg["theme"]
            self.stretch_on = bool(cfg.get("stretch", True))
            self.auto_update = bool(cfg.get("auto_update", True))
            if cfg.get("update_channel") in ("stable", "continuous"):
                self.update_channel = cfg["update_channel"]
            self.pet_name = str(cfg.get("pet_name") or "Dogi")[:24]
            self.show_control_center_on_start = bool(
                cfg.get("show_control_center_on_start", True)
            )
            if cfg.get("sound_style") in SOUND_CHOICES:
                self.sound_style = cfg["sound_style"]
            self.rest_reminder_on = bool(cfg.get("rest_reminder", True))
            if cfg.get("rest_after_min") in REST_CHOICES:
                self.rest_after_min = cfg["rest_after_min"]
            self.scroll_reaction_on = bool(cfg.get("scroll_reaction", True))
            self.meeting_reaction_on = bool(cfg.get("meeting_reaction", True))
            self.meeting_bark_on = bool(cfg.get("meeting_bark", True))
            self.presentation_hide_on = bool(cfg.get("presentation_hide", True))
            model = str(cfg.get("ai_model") or DEFAULT_AI_MODEL).strip()
            self.ai_model = model[:80] or DEFAULT_AI_MODEL
            reminder = cfg.get(
                "calendar_reminder_min", DEFAULT_CALENDAR_REMINDER_MIN
            )
            if reminder in (5, 10, 15, 30):
                self.calendar_reminder_min = reminder
            raw_stats = cfg.get("stats") or {}
            for key in self.stats:
                if isinstance(raw_stats.get(key), (int, float)):
                    self.stats[key] = clamp_stat(raw_stats[key])
            stats_ts = cfg.get("stats_ts")
            if isinstance(stats_ts, (int, float)) and stats_ts < time.time():
                offline_minutes = (time.time() - stats_ts) / 60
                self.stats = offline_decay(self.stats, offline_minutes)
            self.last_greet_date = str(cfg.get("last_greet_date") or "")
            self.last_lunch_date = str(cfg.get("last_lunch_date") or "")
        except Exception:
            pass

    def save_config(self):
        try:
            CONF_DIR.mkdir(exist_ok=True)
            primary = self.pets[0].theme if self.pets else self.theme
            CONF_FILE.write_text(
                json.dumps(
                    {
                        "theme": primary,
                        "stretch": self.stretch_on,
                        "auto_update": self.auto_update,
                        "update_channel": self.update_channel,
                        "pet_name": self.pet_name,
                        "show_control_center_on_start": self.show_control_center_on_start,
                        "sound_style": self.sound_style,
                        "rest_reminder": self.rest_reminder_on,
                        "rest_after_min": self.rest_after_min,
                        "scroll_reaction": self.scroll_reaction_on,
                        "meeting_reaction": self.meeting_reaction_on,
                        "meeting_bark": self.meeting_bark_on,
                        "presentation_hide": self.presentation_hide_on,
                        "ai_model": self.ai_model,
                        "calendar_reminder_min": self.calendar_reminder_min,
                        "stats": {k: round(v, 2) for k, v in self.stats.items()},
                        "stats_ts": time.time(),
                        "last_greet_date": self.last_greet_date,
                        "last_lunch_date": self.last_lunch_date,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ------------------------------------------------------------- input
    def _on_key(self, _key, _injected=False):
        self.last_key_time = time.time()

    def _on_scroll(self, _x, _y, _dx, dy, _injected=False):
        self.last_scroll_time = time.time()
        self.scroll_direction = 1 if dy > 0 else -1

    def _cursor(self):
        return self.root.winfo_pointerx(), self.root.winfo_pointery()

    def _check_cursor_swing(self, now, cursor_x):
        direction, triggered = self.cursor_swing.update(cursor_x, now)
        if direction:
            for pet in self.pets:
                # Gerak biasa hanya menggeser pandangan; badan tidak lagi
                # membolak-balik setiap kursor berubah arah.
                pet.gaze_x = cursor_x
                pet.gaze_until = now + 1.5
        if not triggered:
            return False
        for pet in self.pets:
            if pet.state not in (
                "hold", "fetch", "think", "meeting_alert", "meeting_watch",
            ):
                pet.set_state("dizzy")
                pet.show_msg("Waduh... pusing!", 3)
        return True

    # ------------------------------------------------------------- agent
    def _poll_agent_status(self):
        try:
            mtime = STATUS_FILE.stat().st_mtime
        except OSError:
            return
        if mtime == self._status_mtime:
            return
        self._status_mtime = mtime
        try:
            data = json.loads(STATUS_FILE.read_text())
        except Exception:
            return
        status = data.get("status")
        ts = data.get("ts", 0)
        if status == "thinking":
            if not self.agent_thinking:
                self._thinking_since = time.time()
            self.agent_thinking = True
        elif status == "done" and ts > self._last_done_ts:
            self._last_done_ts = ts
            self.agent_thinking = False
            self.celebrate_all("Guk guk! Tugas selesai!")

    def _agent_watchdog(self, now):
        """Lepaskan Dogi bila status 'thinking' nyangkut (sesi agent crash /
        hook 'done' tak pernah tiba), supaya tak membeku selamanya."""
        if self.agent_thinking and now - self._thinking_since > THINK_WATCHDOG_S:
            self.agent_thinking = False

    # ----------------------------------------------- catatan AI & kalender
    def has_openai_key(self):
        try:
            return bool(self.secure_store.get("openai_api_key", ""))
        except SecureStoreError:
            return False

    def set_openai_key(self, api_key):
        key = str(api_key or "").strip()
        if not key:
            self.secure_store.delete("openai_api_key")
            return
        self.secure_store.set("openai_api_key", key)

    def organize_note_async(self, text, callback):
        """Rapikan satu catatan tanpa memblokir animasi Tk."""
        try:
            api_key = self.secure_store.get("openai_api_key", "")
        except SecureStoreError as exc:
            callback(None, str(exc))
            return False
        if not api_key:
            callback(None, "API key OpenAI belum diatur.")
            return False

        def worker():
            try:
                result = organize_note(text, api_key, model=self.ai_model)
                error = None
            except Exception as exc:
                result, error = None, str(exc)
            try:
                self.root.after(0, lambda: callback(result, error))
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()
        return True

    def connect_google_calendar_async(self, credentials_path, callback=None):
        if self._calendar_syncing:
            return False
        self._calendar_syncing = True
        self.calendar_status = "MENUNGGU LOGIN GOOGLE DI BROWSER..."

        def worker():
            try:
                if credentials_path:
                    self.calendar_integration.import_client(credentials_path)
                self.calendar_integration.authorize()
                events = self.calendar_integration.upcoming()
                error = None
            except Exception as exc:
                events, error = [], str(exc)
            try:
                self.root.after(
                    0,
                    lambda: self._finish_calendar_sync(
                        events, error, callback=callback, connected=True
                    ),
                )
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()
        return True

    def sync_google_calendar_async(self, manual=False, callback=None):
        if self._calendar_syncing:
            return False
        if not self.calendar_connected:
            self.calendar_status = "GOOGLE CALENDAR BELUM TERHUBUNG"
            if manual and callback:
                callback(False, "Hubungkan Google Calendar lebih dulu.")
            return False

        self._calendar_syncing = True
        self.calendar_status = "MENYINKRONKAN AGENDA..."

        def worker():
            try:
                events = self.calendar_integration.upcoming()
                error = None
            except Exception as exc:
                events, error = [], str(exc)
            try:
                self.root.after(
                    0,
                    lambda: self._finish_calendar_sync(
                        events, error, callback=callback, connected=False
                    ),
                )
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()
        return True

    def _finish_calendar_sync(self, events, error, callback=None, connected=False):
        self._calendar_syncing = False
        now = time.time()
        if error:
            self.calendar_status = f"GAGAL: {error}".upper()[:80]
            self._calendar_sync_at = now + CALENDAR_RETRY_SECONDS
        else:
            self.calendar_connected = True
            self.calendar_events = list(events)
            count = len(self.calendar_events)
            self.calendar_status = f"TERHUBUNG  /  {count} AGENDA 7 HARI"
            self._calendar_sync_at = now + CALENDAR_SYNC_SECONDS
            valid_ids = {event.id for event in self.calendar_events}
            self._calendar_reminded.intersection_update(valid_ids)
            if connected and self.pets:
                self.pets[0].show_msg("Kalender terhubung!", 4)
        if self.control_center:
            self.control_center.sync_from_app()
        if callback:
            callback(not error, error)

    def disconnect_google_calendar(self):
        try:
            self.calendar_integration.disconnect()
        except SecureStoreError as exc:
            raise CalendarIntegrationError(str(exc)) from exc
        self.calendar_events = []
        self.calendar_connected = False
        self._calendar_reminded.clear()
        self._calendar_sync_at = 0.0
        self.calendar_status = "GOOGLE CALENDAR BELUM TERHUBUNG"

    def _check_calendar(self, now):
        if self.smoke_test:
            return
        if self.calendar_connected and now >= self._calendar_sync_at:
            self.sync_google_calendar_async()
        if not self.calendar_events:
            return

        current = datetime.fromtimestamp(now).astimezone()
        for event in self.calendar_events:
            if not reminder_due(
                event,
                current,
                self.calendar_reminder_min,
                self._calendar_reminded,
            ):
                continue
            self._calendar_reminded.add(event.id)
            remaining = max(
                0, int((event.start.astimezone() - current).total_seconds() / 60)
            )
            title = event.title.strip()[:24] or "Agenda"
            message = f"{title}: {remaining} mnt lagi"
            if self.pets:
                pet = self.pets[0]
                pet.set_state("meeting_alert")
                pet.show_msg(message, 8)
            bark(self.root, self.sound_style)

    # ------------------------------------------------------- kebutuhan & jam
    def on_fed(self):
        self.stats["kenyang"] = clamp_stat(self.stats["kenyang"] + 35)
        self.stats["senang"] = clamp_stat(self.stats["senang"] + 8)

    def on_petted(self):
        self.stats["senang"] = clamp_stat(self.stats["senang"] + 10)

    def state_weights(self):
        """Bobot perilaku spontan sesuai jam, energi, dan suasana hati."""
        idle, walk, sleep, dig = 4, 4, 1, 1
        curious, tail_wag, beg, zoomies = 2, 2, 1, 1
        spin, sniff, pee = 1, 2, 1
        if is_night(time.localtime().tm_hour):
            idle, walk, sleep, dig = 2, 1, 6, 0
            curious, tail_wag, beg, zoomies = 1, 1, 0, 0
            spin, sniff, pee = 0, 1, 0
        if self.stats["energi"] < NEED_LOW:
            sleep += 4
            walk = max(1, walk - 2)
            zoomies = 0
            spin = 0
        if self.stats["senang"] < NEED_LOW:
            walk = max(1, walk - 1)  # lesu, malas jalan-jalan
            beg += 3
        return [idle, walk, sleep, dig, curious, tail_wag, beg, zoomies,
                spin, sniff, pee]

    def _update_stats(self, now):
        minutes = (now - self._last_stats_tick) / 60
        self._last_stats_tick = now
        if minutes <= 0:
            return
        sleeping = bool(self.pets) and self.pets[0].state == "sleep"
        self.stats = decay_stats(self.stats, minutes, sleeping=sleeping)
        if now - self._stats_saved > 60:
            self._stats_saved = now
            self.save_config()

    def _schedule_mischief(self, now):
        self._mischief_at = now + random.uniform(
            MISCHIEF_MIN_GAP, MISCHIEF_MAX_GAP
        )

    def _check_mischief(self, now):
        """Sesekali Dogi berulah usil: nyeletuk, muter, atau lari gembira."""
        if now < self._mischief_at:
            return
        self._schedule_mischief(now)
        if not self.pets:
            return
        pet = self.pets[0]
        # jangan usil saat sedang sibuk kerja, lelah, atau malam hari
        if pet.state not in ("idle", "walk", "curious", "sniff", "tail_wag"):
            return
        if is_night(time.localtime(now).tm_hour):
            return
        if HAS_PYNPUT and now - self.last_key_time < 3.0:
            return
        if self.stats["energi"] < NEED_LOW:
            return
        roll = random.random()
        if roll < 0.4:
            pet.show_msg(random.choice(MISCHIEF_MESSAGES), 5)
            pet.set_state("beg")
        elif roll < 0.7:
            pet.set_state("spin")
            pet.show_msg(random.choice(SPIN_MESSAGES), 3)
        else:
            pet.set_state("zoomies")
            pet.show_msg(random.choice(MISCHIEF_MESSAGES), 3)
        self.stats["senang"] = clamp_stat(self.stats["senang"] + 3)

    def _check_needs(self, now):
        """Dogi merengek lewat bubble saat ada kebutuhan yang rendah."""
        if now < self._nag_cd or not self.pets:
            return
        pet = self.pets[0]
        if pet.state not in ("idle", "walk", "dig"):
            return
        if self.stats["kenyang"] < NEED_LOW:
            msg = random.choice(("Aku lapar...", "Ada tulang, nggak?"))
        elif self.stats["energi"] < NEED_LOW:
            msg = "Ngantuk banget..."
        elif self.stats["senang"] < NEED_LOW:
            msg = "Elus aku dong..."
        else:
            return
        pet.show_msg(msg, 4)
        self._nag_cd = now + NAG_COOLDOWN

    def _check_rest(self, now, active):
        """Ajak istirahat bila pengguna aktif nonstop melewati ambang."""
        minutes = self.activity.update(now, active)
        if not self.rest_reminder_on:
            self._rest_exceeded = False
            self._rest_nag_at = 0.0
            return
        if minutes >= self.rest_after_min and now >= self._rest_nag_at:
            self._rest_nag_at = now + REST_NAG_EVERY_S
            self._rest_exceeded = True
            if self.pets:
                pet = self.pets[0]
                pet.show_msg(f"Sudah {int(minutes)} menit. Rehat, yuk!", 8)
                if pet.state in ("idle", "walk", "dig", "type"):
                    pet.set_state("happy")  # lompat kecil minta perhatian
            bark(self.root, self.sound_style)
        elif self._rest_exceeded and minutes == 0:
            self._rest_exceeded = False
            self._rest_nag_at = 0.0
            if self.pets:
                self.pets[0].set_state("happy")
                self.pets[0].show_msg("Segar lagi! Guk!", 5)

    def _check_clock(self, now):
        """Sapaan pagi sekali sehari dan pengingat makan siang."""
        if now < self._clock_cd:
            return
        self._clock_cd = now + 10
        local = time.localtime(now)
        today = time.strftime("%Y-%m-%d", local)
        if is_morning(local.tm_hour) and self.last_greet_date != today:
            self.last_greet_date = today
            if self.pets:
                self.pets[0].show_msg("Selamat pagi! Guk!", 6)
                self.pets[0].set_state("happy")
            self.save_config()
        elif local.tm_hour == LUNCH_HOUR and self.last_lunch_date != today:
            self.last_lunch_date = today
            if self.pets:
                self.pets[0].show_msg("Waktunya makan siang!", 6)
            self.save_config()

    def _check_meeting(self, now):
        """Deteksi jendela rapat, arahkan Dogi, lalu beri reaksi seperlunya."""
        if self.smoke_test:
            return
        if not self.meeting_reaction_on:
            self.meeting_active = False
            self.meeting_title = ""
            self._meeting_key = None
            return
        if now < self._meeting_poll_at:
            return
        self._meeting_poll_at = now + MEETING_POLL_SECONDS

        windows = visible_meeting_windows()
        if not windows:
            if now - self._meeting_last_seen > MEETING_LOST_GRACE_SECONDS:
                self.meeting_active = False
                self.meeting_title = ""
                self._meeting_key = None
            return

        meeting = windows[0]
        key = (meeting["hwnd"], meeting["executable"].lower())
        is_new = key != self._meeting_key
        self._meeting_key = key
        self._meeting_last_seen = now
        self.meeting_active = True
        self.meeting_title = pathlib.Path(meeting["executable"]).stem

        # Selama meeting aktif, semua Dogi melihat ke pusat jendela rapat.
        for pet in self.pets:
            if meeting["center_x"] != pet.center_x():
                pet.facing = 1 if meeting["center_x"] > pet.center_x() else -1

        if not self.pets:
            return
        primary = self.pets[0]
        if is_new:
            self._meeting_watch_at = now + MEETING_WATCH_EVERY_SECONDS
            if not (primary._drag_start and primary._moved):
                primary.set_state("meeting_alert")
                primary.show_msg(
                    random.choice(
                        (
                            "Guk! Siapa itu?",
                            "Ada orang baru!",
                            "Aku jagain meetingnya!",
                        )
                    ),
                    6,
                )
                if self.meeting_bark_on:
                    bark(self.root, self.sound_style)
        elif now >= self._meeting_watch_at:
            self._meeting_watch_at = now + MEETING_WATCH_EVERY_SECONDS
            if primary.state in (
                "idle", "walk", "dig", "curious", "tail_wag", "beg",
            ):
                primary.set_state("meeting_watch")
                primary.show_msg(
                    random.choice(("Aku masih ngawasin.", "Meetingnya aman!")),
                    5,
                )

    # ------------------------------------------------------------- aksi
    def celebrate_all(self, msg):
        bark(self.root, self.sound_style)
        for i, pet in enumerate(self.pets):
            pet.celebrate(msg if i == 0 else None)

    def toggle_pomodoro(self):
        if self.pomo_end:
            self.pomo_end = None
            if self.pets:
                self.pets[0].show_msg("Pomodoro dibatalkan", 3)
        else:
            self.pomo_end = time.time() + POMODORO_MIN * 60
            if self.pets:
                self.pets[0].show_msg(
                    f"Fokus {POMODORO_MIN} menit dimulai!", 4
                )
        if self.control_center:
            self.control_center.sync_from_app()

    def toggle_stretch(self):
        self.stretch_on = not self.stretch_on
        self.last_stretch = time.time()
        self.save_config()
        if self.control_center:
            self.control_center.sync_from_app()

    def toggle_rest_reminder(self):
        self.rest_reminder_on = not self.rest_reminder_on
        self._rest_nag_at = 0.0
        self.save_config()
        if self.pets:
            status = "aktif" if self.rest_reminder_on else "nonaktif"
            self.pets[0].show_msg(f"Ajak istirahat {status}", 3)
        if self.control_center:
            self.control_center.sync_from_app()

    def set_rest_after(self, minutes):
        if minutes not in REST_CHOICES:
            return
        self.rest_after_min = minutes
        self._rest_nag_at = 0.0
        self.save_config()
        if self.control_center:
            self.control_center.sync_from_app()

    def set_sound_style(self, style):
        if style not in SOUND_CHOICES:
            return
        self.sound_style = style
        ensure_bark_wav(style)
        self.save_config()
        if self.pets:
            self.pets[0].show_msg(
                "Senyap, ya..." if style == "senyap" else "Guk guk!", 2
            )
        bark(self.root, style)  # pratinjau langsung
        if self.control_center:
            self.control_center.sync_from_app()

    def toggle_scroll_reaction(self):
        self.scroll_reaction_on = not self.scroll_reaction_on
        self.save_config()
        if self.control_center:
            self.control_center.sync_from_app()

    def toggle_meeting_reaction(self):
        self.meeting_reaction_on = not self.meeting_reaction_on
        self._meeting_poll_at = 0.0
        if not self.meeting_reaction_on:
            self.meeting_active = False
            self.meeting_title = ""
            self._meeting_key = None
        self.save_config()
        if self.control_center:
            self.control_center.sync_from_app()

    def toggle_meeting_bark(self):
        self.meeting_bark_on = not self.meeting_bark_on
        self.save_config()
        if self.control_center:
            self.control_center.sync_from_app()

    def toggle_presentation_hide(self):
        self.presentation_hide_on = not self.presentation_hide_on
        self._presentation_checked = 0.0
        self.save_config()
        if self.pets:
            status = "aktif" if self.presentation_hide_on else "nonaktif"
            self.pets[0].show_msg(f"Mode presentasi {status}", 3)
        if self.control_center:
            self.control_center.sync_from_app()

    def toggle_startup(self):
        try:
            startup_registry.set_enabled(not self.startup_on)
        except startup_registry.StartupError as exc:
            messagebox.showwarning("DogiPet", str(exc))
            return
        self.startup_on = startup_registry.is_enabled()
        if self.pets:
            status = "aktif" if self.startup_on else "nonaktif"
            self.pets[0].show_msg(f"Jalan saat startup {status}", 3)
        if self.control_center:
            self.control_center.sync_from_app()

    def _apply_presentation(self, now):
        """Sembunyikan Dogi saat aplikasi fullscreen di depan (presentasi)."""
        want_hidden = False
        if self.presentation_hide_on:
            if now - self._presentation_checked < 1.0:
                return
            self._presentation_checked = now
            want_hidden = foreground_fullscreen_active()
        if want_hidden == self._hidden_for_presentation:
            return
        self._hidden_for_presentation = want_hidden
        for pet in self.pets:
            try:
                pet.win.withdraw() if want_hidden else pet.win.deiconify()
            except tk.TclError:
                pass
        for bone in self.bones:
            try:
                bone.win.withdraw() if want_hidden else bone.win.deiconify()
            except tk.TclError:
                pass

    def toggle_auto_update(self):
        self.auto_update = not self.auto_update
        self.save_config()
        if self.pets:
            status = "aktif" if self.auto_update else "nonaktif"
            self.pets[0].show_msg(f"Auto-update {status}", 3)
        if self.control_center:
            self.control_center.sync_from_app()

    def set_update_channel(self, channel):
        if channel not in ("stable", "continuous"):
            return
        self.update_channel = channel
        self.save_config()
        if self.pets:
            self.pets[0].show_msg(f"Kanal: {channel}", 3)
        if self.control_center:
            self.control_center.sync_from_app()
        self.check_updates(manual=True)

    def show_control_center(self):
        if self.control_center:
            self.control_center.show()

    def check_updates(self, manual=False):
        started = self.update_manager.check_async(
            channel=self.update_channel,
            manual=manual,
        )
        if started and manual and self.pets:
            self.pets[0].show_msg("Memeriksa pembaruan...", 3)
        elif not started and manual:
            messagebox.showinfo(
                "Pembaruan DogiPet",
                "Pemeriksaan atau unduhan pembaruan masih berjalan.",
            )

    def _poll_update_events(self):
        for event, payload in self.update_manager.poll():
            if event == "available":
                info = payload
                if not isinstance(info, UpdateInfo):
                    continue
                build_label = info.version
                if info.channel == "continuous" and info.build_id:
                    build_label = f"{info.version} ({info.build_id[:8]})"
                install = messagebox.askyesno(
                    "Pembaruan DogiPet tersedia",
                    f"DogiPet {build_label} tersedia.\n\n"
                    "Unduh dan pasang sekarang? Aplikasi akan dimulai ulang.",
                )
                if install:
                    self._installer_pending = info
                    self.update_manager.download_async(info)
                    if self.pets:
                        self.pets[0].show_msg("Mengunduh pembaruan...", 8)
            elif event == "current" and payload:
                messagebox.showinfo(
                    "Pembaruan DogiPet",
                    "DogiPet yang terpasang sudah versi terbaru.",
                )
            elif event == "error":
                error, manual = payload
                if manual:
                    messagebox.showwarning("Pembaruan DogiPet", str(error))
            elif event == "download_error":
                self._installer_pending = None
                messagebox.showerror("Pembaruan DogiPet", str(payload))
            elif event == "downloaded":
                try:
                    launch_installer(payload)
                except Exception as exc:
                    messagebox.showerror("Pembaruan DogiPet", str(exc))
                    self._installer_pending = None
                else:
                    self.root.after(150, self.quit)

    def add_pet(self):
        if len(self.pets) >= MAX_PETS:
            return
        used = {p.theme for p in self.pets}
        pool = [t for t in COLOR_THEMES if t not in used] \
            or list(COLOR_THEMES)
        x = random.randint(
            self.screen_left + 40,
            max(self.screen_left + 41, self.screen_right - CANVAS_W - 40),
        )
        self.pets.append(DogiPet(self, x, random.choice(pool)))
        if self.control_center:
            self.control_center.sync_from_app()

    def remove_pet(self, pet):
        if len(self.pets) <= 1:
            return
        pet.destroy()
        self.pets.remove(pet)
        if pet.primary and self.pets:
            self.pets[0].primary = True
            self.theme = self.pets[0].theme
        if self.control_center:
            self.control_center.sync_from_app()

    def spawn_bone(self):
        if len(self.bones) >= 3 or not self.pets:
            return
        # pilih Dogi terdekat yang sedang senggang
        free = [p for p in self.pets if p.state in (
            "idle", "walk", "sleep", "dig", "think", "curious",
            "tail_wag", "beg", "glance", "sniff", "pee",
        )]
        # Jangan menimpa fetch yang masih aktif. Sebelumnya klik berulang dapat
        # memindahkan referensi pet ke tulang baru dan membuat tulang lama
        # tidak pernah diambil.
        if not free:
            self.pets[0].show_msg("Sebentar, aku masih sibuk!", 3)
            return
        x = random.randint(
            self.screen_left + 40,
            max(self.screen_left + 41, self.screen_right - BONE_W - 40),
        )
        pet = min(free, key=lambda p: abs(p.center_x() - x))
        y = pet.y + CANVAS_H - BONE_H - 6
        bone = Bone(self, x, y)
        self.bones.append(bone)
        pet.fetch_bone = bone
        pet.set_state("fetch")

    def remove_bone(self, bone):
        bone.destroy()
        if bone in self.bones:
            self.bones.remove(bone)

    def _check_friends(self, now):
        """Dua Dogi berpapasan -> saling menyapa dengan gembira."""
        if now < self._friend_cd:
            return
        for i in range(len(self.pets)):
            for j in range(i + 1, len(self.pets)):
                a, b = self.pets[i], self.pets[j]
                if a.state in ("idle", "walk", "dig", "curious", "tail_wag", "beg") \
                        and b.state in ("idle", "walk", "dig", "curious", "tail_wag", "beg") \
                        and abs(a.center_x() - b.center_x()) < FRIEND_DIST \
                        and abs(a.y - b.y) < 80:
                    a.facing = 1 if b.x > a.x else -1
                    b.facing = -a.facing
                    a.set_state("happy")
                    b.set_state("happy")
                    a.show_msg("Guk!", 2)
                    b.show_msg("Guk guk!", 2)
                    self._friend_cd = now + FRIEND_COOLDOWN
                    return

    # ------------------------------------------------------------- loop utama
    def _tick(self):
        now = time.time()
        cx, cy = self._cursor()

        self._check_cursor_swing(now, cx)

        self._poll_agent_status()
        self._agent_watchdog(now)
        self._poll_update_events()
        self._update_stats(now)
        self._check_clock(now)
        self._check_needs(now)
        self._check_mischief(now)
        self._check_meeting(now)
        self._check_calendar(now)
        self._apply_presentation(now)

        if self.pomo_end and now >= self.pomo_end:
            self.pomo_end = None
            self.celebrate_all(
                f"Pomodoro selesai! Istirahat {BREAK_MIN} menit"
            )
        if self.stretch_on \
                and now - self.last_stretch > STRETCH_EVERY_MIN * 60:
            self.last_stretch = now
            self.celebrate_all("Peregangan dulu, yuk!")

        typing = HAS_PYNPUT and (now - self.last_key_time) < 1.2
        scrolling = (
            self.scroll_direction
            if HAS_PYNPUT
            and now - self.last_scroll_time < SCROLL_REACTION_SECONDS
            else 0
        )
        moved = (
            abs(cx - self.last_cursor[0]) + abs(cy - self.last_cursor[1]) > 3
        )
        self._check_rest(now, typing or moved)

        for pet in self.pets:
            pet.tick(
                now, cx, cy, typing, self.agent_thinking, scrolling=scrolling
            )

        self._check_friends(now)
        self.last_cursor = (cx, cy)

        for pet in self.pets:
            pet.draw(cx, cy)
            pet.place()

        self.root.after(TICK_MS, self._tick)

    def quit(self):
        self.save_config()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if "--hook" in sys.argv:
        # dipanggil dari hook Claude Code pada build frozen; tanpa UI
        index = sys.argv.index("--hook")
        status = sys.argv[index + 1] if index + 1 < len(sys.argv) else "done"
        dogi_hook.write_status(status)
        raise SystemExit(0)
    is_smoke_test = "--smoke-test" in sys.argv
    if not acquire_single_instance(smoke_test=is_smoke_test):
        raise SystemExit(0)
    application = DogiApp(
        smoke_test=is_smoke_test,
        opaque_preview="--opaque-preview" in sys.argv,
    )
    state_argument = next(
        (arg.split("=", 1)[1].lower() for arg in sys.argv if arg.startswith("--state=")),
        None,
    )
    if state_argument in FRAMES and application.pets:
        application.pets[0].set_state(state_argument, 999999)
    page_argument = next(
        (arg.split("=", 1)[1].upper() for arg in sys.argv if arg.startswith("--page=")),
        None,
    )
    if page_argument in application.control_center.pages:
        application.control_center.show_page(page_argument)
        application.root.after(50, application.show_control_center)
    if is_smoke_test:
        application.root.after(1200, application.quit)
    application.run()
