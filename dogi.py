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
from tkinter import messagebox
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
FETCH_SPEED = 7
CHASE_SPEED = 9
CHASE_RANGE = 350
TRANSPARENT = "#ff00fe"

GRID_W, GRID_H = 16, 12
SPR_W, SPR_H = GRID_W * SCALE, GRID_H * SCALE
BUBBLE_H = 36
CANVAS_W = 230
CANVAS_H = BUBBLE_H + SPR_H
SPR_X = (CANVAS_W - SPR_W) // 2
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
BARK_FILE = CONF_DIR / "bark.wav"

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

FRAMES = {
    "idle":  [IDLE_1, IDLE_2],
    "walk":  [WALK_1, WALK_2],
    "chase": [WALK_1, WALK_2],
    "fetch": [WALK_1, WALK_2],
    "sleep": [SLEEP_1, SLEEP_2],
    "happy": [HAPPY_1, HAPPY_2],
    "dig":   [DIG_1, DIG_2],
    "eat":   [EAT_1, EAT_2],
    "think": [IDLE_1, IDLE_1],
    "jump":  [HAPPY_1, HAPPY_2],
}

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
def ensure_bark_wav():
    """Sintesis file WAV gonggongan 'guk-guk' saat pertama dijalankan."""
    if BARK_FILE.exists():
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

        burst(650, 280, 0.10, 0.9)                    # "guk"
        samples.extend([0] * int(sr * 0.06))          # jeda
        burst(560, 240, 0.13, 0.9)                    # "guk!"

        with wave.open(str(BARK_FILE), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    except Exception:
        pass


def bark(root):
    def _go():
        try:
            if HAS_SOUND and BARK_FILE.exists():
                winsound.PlaySound(
                    str(BARK_FILE),
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
        self.win.geometry(f"{BONE_W}x{BONE_H}+{int(x)}+{int(y)}")

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
        self.ground_y = app.screen_h - CANVAS_H - 60
        self.y = self.ground_y

        self.state = "idle"
        self.state_timer = random.randint(20, 50)
        self.frame_i = random.randint(0, 1)
        self.facing = random.choice([1, -1])
        self.target_x = x
        self.blink = False
        self.temp_msg = None
        self.fetch_bone = None

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

    def place(self):
        self.win.geometry(
            f"{CANVAS_W}x{CANVAS_H}+{int(self.x)}+{int(self.y)}"
        )

    def palette(self):
        pal = dict(FIXED_COLORS)
        pal.update(COLOR_THEMES[self.theme])
        return pal

    def set_state(self, state, duration=None):
        if self.state == "fetch" and state != "fetch":
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
                "eat":   22,
                "think": 999999,
                "jump":  len(JUMP_ARC),
            }[state]
        self.state_timer = duration
        if state == "walk":
            margin = 80
            self.target_x = random.randint(
                margin, self.app.screen_w - CANVAS_W - margin
            )
            self.facing = 1 if self.target_x > self.x else -1

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

    def draw(self, cx, cy):
        self.canvas.delete("all")
        pal = self.palette()
        frame = FRAMES[self.state][self.frame_i % 2]
        if self.facing == -1 and self.state != "sleep":
            frame = mirror(frame)
        if self.state in ("idle", "walk", "chase", "fetch", "think", "dig"):
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
    def tick(self, now, cx, cy, typing, thinking):
        # status agent AI (prioritas tertinggi)
        if thinking and self.state not in ("think", "jump"):
            self.set_state("think")
        elif not thinking and self.state == "think":
            self.set_state("idle")

        # mengetik -> Dogi ikut sibuk: menggali dengan semangat
        if typing and self.state in ("idle", "walk", "sleep"):
            self.set_state("dig")
        if self.state == "dig" and not typing \
                and now - self.app.last_key_time > 2.0:
            self.set_state("idle")

        # naluri berburu kursor
        if self.state in ("idle", "walk"):
            speed = (
                abs(cx - self.app.last_cursor[0])
                + abs(cy - self.app.last_cursor[1])
            )
            dist = abs(cx - self.center_x())
            if speed > 60 and dist < CHASE_RANGE:
                self.set_state("chase")

        # pergerakan
        if self.state == "walk":
            self.x += WALK_SPEED * self.facing
            if (self.facing == 1 and self.x >= self.target_x) or \
               (self.facing == -1 and self.x <= self.target_x):
                self.set_state("idle")

        elif self.state == "chase":
            target = cx - CANVAS_W // 2
            self.facing = 1 if target > self.x else -1
            if abs(target - self.x) > CHASE_SPEED:
                self.x += CHASE_SPEED * self.facing
            else:
                self.x = target
                self.set_state("happy")

        elif self.state == "fetch" and self.fetch_bone:
            target = self.fetch_bone.x - CANVAS_W // 2 + BONE_W // 2
            self.facing = 1 if target > self.x else -1
            if abs(target - self.x) > FETCH_SPEED:
                self.x += FETCH_SPEED * self.facing
            else:
                self.x = target
                self.app.remove_bone(self.fetch_bone)
                self.fetch_bone = None
                bark(self.app.root)
                self.show_msg("Nyam nyam!", 3)
                self.set_state("eat")

        elif self.state == "jump":
            i = len(JUMP_ARC) - self.state_timer
            i = max(0, min(len(JUMP_ARC) - 1, i))
            self.y = self.ground_y - JUMP_ARC[i]

        # batas layar & kedipan
        self.x = max(0, min(self.app.screen_w - CANVAS_W, self.x))
        self.blink = (
            self.state in ("idle", "dig", "think")
            and random.random() < 0.08
        )

        # transisi state
        self.state_timer -= 1
        if self.state_timer <= 0:
            if self.state == "jump":
                self.y = self.ground_y
                self.set_state("happy", 8)
            elif self.state == "eat":
                self.set_state("happy")
            elif self.state in ("sleep", "happy", "dig"):
                self.set_state("idle")
            elif self.state not in ("think", "fetch"):
                nxt = random.choices(
                    ["idle", "walk", "sleep"], weights=[4, 4, 1]
                )[0]
                self.set_state(nxt)

        self.frame_i += 2 if self.state == "dig" else 1

    # ------------------------------------------------------------- interaksi
    def _on_press(self, e):
        self._drag_start = (e.x_root, e.y_root, self.x, self.y)
        self._moved = False

    def _on_drag(self, e):
        if not self._drag_start:
            return
        sx, sy, ox, oy = self._drag_start
        dx, dy = e.x_root - sx, e.y_root - sy
        if abs(dx) + abs(dy) > 4:
            self._moved = True
        self.x = ox + dx
        self.y = oy + dy
        self.place()

    def _on_release(self, e):
        if not self._moved:
            self.set_state("happy")
        else:
            self.ground_y = self.y
        self._drag_start = None

    def _set_theme(self, name):
        self.theme = name
        if self.primary:
            self.app.save_config()

    def _on_menu(self, e):
        app = self.app
        menu = tk.Menu(self.win, tearoff=0)

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


# ------------------------------------------------------------- aplikasi utama
class DogiApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # root disembunyikan; tiap Dogi punya jendela

        self.transparent_ok = False
        if sys.platform.startswith("win"):
            probe = tk.Toplevel(self.root)
            try:
                probe.attributes("-transparentcolor", TRANSPARENT)
                self.transparent_ok = True
            except tk.TclError:
                pass
            probe.destroy()

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # fitur bersama
        self.pomo_end = None
        self.stretch_on = True
        self.last_stretch = time.time()
        self.agent_thinking = False
        self._status_mtime = 0
        self._last_done_ts = 0
        self.last_key_time = 0
        self.last_cursor = (0, 0)
        self._friend_cd = 0

        self.auto_update = True
        self.update_channel = "continuous"
        self.update_manager = UpdateManager()
        self._installer_pending = None

        self.theme = "Shiba"
        self._load_config()
        ensure_bark_wav()

        if HAS_PYNPUT:
            listener = _pynput_keyboard.Listener(on_press=self._on_key)
            listener.daemon = True
            listener.start()

        self.pets = [
            DogiPet(
                self, (self.screen_w - CANVAS_W) // 2,
                self.theme, primary=True,
            )
        ]
        self.bones = []

        self.root.after(TICK_MS, self._tick)
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

    def _cursor(self):
        return self.root.winfo_pointerx(), self.root.winfo_pointery()

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
            self.agent_thinking = True
        elif status == "done" and ts > self._last_done_ts:
            self._last_done_ts = ts
            self.agent_thinking = False
            self.celebrate_all("Guk guk! Tugas selesai!")

    # ------------------------------------------------------------- aksi
    def celebrate_all(self, msg):
        bark(self.root)
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

    def toggle_stretch(self):
        self.stretch_on = not self.stretch_on
        self.last_stretch = time.time()
        self.save_config()

    def toggle_auto_update(self):
        self.auto_update = not self.auto_update
        self.save_config()
        if self.pets:
            status = "aktif" if self.auto_update else "nonaktif"
            self.pets[0].show_msg(f"Auto-update {status}", 3)

    def set_update_channel(self, channel):
        if channel not in ("stable", "continuous"):
            return
        self.update_channel = channel
        self.save_config()
        if self.pets:
            self.pets[0].show_msg(f"Kanal: {channel}", 3)
        self.check_updates(manual=True)

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
        x = random.randint(40, max(41, self.screen_w - CANVAS_W - 40))
        self.pets.append(DogiPet(self, x, random.choice(pool)))

    def remove_pet(self, pet):
        if len(self.pets) <= 1:
            return
        pet.destroy()
        self.pets.remove(pet)
        if pet.primary and self.pets:
            self.pets[0].primary = True

    def spawn_bone(self):
        if len(self.bones) >= 3 or not self.pets:
            return
        x = random.randint(40, max(41, self.screen_w - BONE_W - 40))
        # pilih Dogi terdekat yang sedang senggang
        free = [p for p in self.pets
                if p.state in ("idle", "walk", "sleep", "dig")]
        pet = min(
            free or self.pets, key=lambda p: abs(p.center_x() - x)
        )
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
                if a.state in ("idle", "walk", "dig") \
                        and b.state in ("idle", "walk", "dig") \
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

        self._poll_agent_status()
        self._poll_update_events()

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

        for pet in self.pets:
            pet.tick(now, cx, cy, typing, self.agent_thinking)

        self._check_friends(now)
        self.last_cursor = (cx, cy)

        for pet in self.pets:
            pet.draw(cx, cy)
            pet.place()

        self.root.after(TICK_MS, self._tick)

    def quit(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    application = DogiApp()
    if "--smoke-test" in sys.argv:
        application.root.after(1200, application.quit)
    application.run()
