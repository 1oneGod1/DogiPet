"""Sprite Dogi yang digambar tangan, frame demi frame.

Setiap frame dikomposisi dari part grid teks (kepala, badan, kaki, prop) pada
kanvas logis 32x28, lalu dirender menjadi PNG 160x140 (blok keras 5x5) untuk
seluruh tema warna plus mirror `_left`. Tidak ada sumber AI ataupun proses
downscale: setiap piksel diletakkan dengan sengaja agar siluet tetap bersih
dan konsisten antar frame.

Pemakaian:
    python scripts/draw_sprites.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "sprites"
GRID_W, GRID_H = 32, 28
BLOCK = 5
FRAME_SIZE = (GRID_W * BLOCK, GRID_H * BLOCK)

# ------------------------------------------------------------------- palet
# o/c/k diganti per tema; sisanya warna tetap untuk semua tema.
FIXED = {
    "n": "#2b1c10",  # mata
    "N": "#2b1c10",  # hidung
    "p": "#f2748c",  # lidah
    "r": "#ff5a79",  # hati / penanda scroll
    "z": "#7fb4e8",  # Zzz / gelombang suara
    "w": "#efe9dc",  # tulang / kilau mata
    "d": "#a8865c",  # debu galian
    "g": "#2a2f36",  # bodi laptop
    "l": "#aab4bd",  # keyboard / engsel
    "b": "#5be0ff",  # baris kode di layar
    "e": "#20242a",  # latar layar
    "y": "#ecd24a",  # genangan pipis
    "s": "#aeb8c0",  # asap lelah mengetik
}

THEMES = {
    "Shiba":  {"o": "#e8a44c", "c": "#f6ddb0", "k": "#5a3a21"},
    "Husky":  {"o": "#9aa7b5", "c": "#f2f2f2", "k": "#3d4653"},
    "Coklat": {"o": "#8a5a33", "c": "#c99a6b", "k": "#4a2d14"},
    "Hitam":  {"o": "#454545", "c": "#9a9a9a", "k": "#141414"},
    "Golden": {"o": "#e6c46a", "c": "#f7ecc7", "k": "#7a5a1f"},
    "Putih":  {"o": "#f4f0e6", "c": "#ffffff", "k": "#9a938a"},
}

VALID_CHARS = set("ocknNprzwdglbeys.")


# -------------------------------------------------------------- kompositor
def part(text: str) -> list[str]:
    rows = [line.strip() for line in text.splitlines() if line.strip()]
    width = max(len(row) for row in rows)
    return [row.ljust(width, ".") for row in rows]


def blank() -> list[list[str]]:
    return [["."] * GRID_W for _ in range(GRID_H)]


def stamp(canvas: list[list[str]], art: list[str], x: int, y: int) -> None:
    """Tempel part ke kanvas; '.' transparan, koordinat boleh keluar tepi."""
    for row_index, row in enumerate(art):
        for col_index, char in enumerate(row):
            if char == ".":
                continue
            gx, gy = x + col_index, y + row_index
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                canvas[gy][gx] = char


def patch(canvas: list[list[str]], cells: list[tuple[int, int, str]]) -> None:
    for gy, gx, char in cells:
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            canvas[gy][gx] = char


def freeze(canvas: list[list[str]]) -> list[str]:
    rows = ["".join(row) for row in canvas]
    assert len(rows) == GRID_H
    for row in rows:
        assert len(row) == GRID_W
        assert set(row) <= VALID_CHARS, sorted(set(row) - VALID_CHARS)
    return rows


# ------------------------------------------------------------ part: kepala
# Kepala menghadap kanan dengan dua kuping shiba yang tinggi, tegak, dan
# runcing. Wajah 3/4 menjaga dua mata tetap ekspresif sementara moncong krem
# dan hidung kecil membentuk profil yang ramah.
HEAD = part("""
...k......k....
..kok....kok...
.kcoook..kcoook.
.koooookkoooook.
koooooooooooook.
koooooooooooook.
koonnooooonnok..
koonnooooonnok..
koooooooooooook.
kooocccccccccNN.
koooccccccccccN.
.kooocccccccck..
..koooooooooook.
...kkkkkkkkkk...
""")

EYES = [(6, 3), (6, 4), (7, 3), (7, 4),
        (6, 9), (6, 10), (7, 9), (7, 10)]


def head_variant(mode: str = "open", pupils: str = "center") -> list[str]:
    """Kepala dengan variasi mata: open/blink/happy/dizzy + arah pupil."""
    grid = [list(row) for row in HEAD]
    if mode == "open":
        # kilau kecil di bawah mata biar hidup
        grid[7][4] = "w"
        grid[7][10] = "w"
        if pupils == "up":
            for col in (3, 4, 9, 10):
                grid[7][col] = "o"
            grid[6][4] = "w"
            grid[6][10] = "w"
        elif pupils == "left":
            for row in (6, 7):
                grid[row][4] = "o"
                grid[row][10] = "o"
            grid[7][3] = "w"
            grid[7][9] = "w"
        elif pupils == "right":
            for row in (6, 7):
                grid[row][3] = "o"
                grid[row][9] = "o"
            grid[7][10] = "w"
            grid[7][4] = "w"
    elif mode in ("blink", "closed"):
        for row, col in EYES:
            grid[row][col] = "o"
        for col in (3, 4, 9, 10):
            grid[7][col] = "k"
    elif mode == "happy":
        # mata melengkung senang: ^ ^
        for row, col in EYES:
            grid[row][col] = "o"
        for col in (3, 4, 9, 10):
            grid[6][col] = "k"
    elif mode == "dizzy":
        for (row, col), char in {
            (6, 3): "n", (6, 4): "w", (7, 3): "w", (7, 4): "n",
            (6, 9): "n", (6, 10): "w", (7, 9): "w", (7, 10): "n",
        }.items():
            grid[row][col] = char
    elif mode == "dizzy2":
        for (row, col), char in {
            (6, 3): "w", (6, 4): "n", (7, 3): "n", (7, 4): "w",
            (6, 9): "w", (6, 10): "n", (7, 9): "n", (7, 10): "w",
        }.items():
            grid[row][col] = char
    return ["".join(row) for row in grid]


HEAD_TONGUE = [(11, 10, "p"), (11, 11, "p"), (12, 10, "p")]
HEAD_BARK = [(10, 12, "k"), (10, 13, "k"), (10, 14, "k"),
             (11, 11, "p"), (11, 12, "p"), (11, 13, "k")]


# Tiga siluet utuh dari konsep low-pixel yang disetujui pengguna. Template
# utuh mencegah anatomi kembali menjadi gabungan kepala + torso kapsul.
APPROVED_STAND = part("""
..............kk..kk..
.............kko.kok..
.............kookkok..
k............koooook..
k...........koooooook.
kk..........koooooook.
kkk.........koooooook.
.kk........koooonoonk.
..kkoooooookooocccccnn
...kooooooooooocccccnn
...kooooooooooooccccpp
..kooooooooooooocck...
..koooooooooooocck....
..kooocc.oooooockk....
..kooocccooooocckk....
..koookkkkkkookkok....
..kokkk....koo.kok....
..kokk.....koo.kock...
..kcko.....kck..ock...
""")

APPROVED_RUN = part("""
..............kk..kk..
.............kko.kok..
.............kookkok..
.............koooooo..
kk..........koooooook.
kkk.........koooooook.
..kk........kooonoonk.
..kk.......kooocccccnn
...kkooooookoooccccckn
...kooooooooooooccccpp
...koooooooooooockk...
..koooooooooooocck....
..koooooooooooocck....
..koooccccckoocckk....
.koookkkkkkkookkook...
kookk.kk...kook.kkok..
kok...kk...kok....okkk
kc.....oo..kk......o..
""")

APPROVED_CROUCH = part("""
.............kk..kk..
............kko.kok..
............kookkok..
k...........koooook..
kk.........koooooook.
kk.........koooooook.
.kkk.......koooooook.
..kk......koooonoonk.
..kkooooookooocccccnn
...koooooooooocccccpp
..kooooooooooooccccpp
..koooooooooooocck...
..kooocooooooocck....
...koockccckookcok...
...kkkckkkkkkckkck...
""")

APPROVED_SLEEP = part("""
..........kk..kk........
.........kko.kok........
.........kookkok........
kk......kooooook........
.kk....kooonoonk........
..kkkkooooocccccnn......
..koooooooooocccccnn....
.kooooooooooooccccccc...
kooccccccccccccccccc....
.kkkkkkkkkkkkkkkkkk.....
""")

APPROVED_HOLD = part("""
....kk..kk......
...kko.kok......
...kookkok......
...koooook......
..kooonoonk.....
..kooocccccnn...
..kooocccccnn...
...koooccccp....
....kkkkkk......
....koooook.....
...koooooook....
...koooooook....
....koooook.....
....koooook.....
....koooook.....
...kok..kok.....
...kok..kok.....
...kkk..kkk.....
""")


# Ekor plume tegak (pilihan pengguna) menggantikan ekor garis tipis lama.
# Dua fase agar berkibas: fase 0 tegak, fase 1 ujung terayun ke depan.
# 'i' = isi ujung krem (jadi 'c').
TAIL_PLUME = {
    0: part("""
.kkk..
kooik.
kook..
kook..
kook..
kook..
.kook.
..kk..
"""),
    1: part("""
..kkk.
.kooik
.kook.
.kook.
kook..
kook..
.kook.
..kk..
"""),
}

# Sel ekor lama yang harus dihapus + titik tempel plume (koordinat template).
POSE_TAIL = {
    "stand": {
        "cells": [(3, 0), (4, 0), (5, 0), (5, 1), (6, 0), (6, 1), (6, 2),
                  (7, 1), (7, 2), (8, 2), (8, 3)],
        "anchor": (1, 1),
    },
    "run": {
        "cells": [(4, 0), (4, 1), (5, 0), (5, 1), (5, 2), (6, 2), (6, 3),
                  (7, 2), (7, 3), (8, 3), (8, 4)],
        "anchor": (1, 2),
    },
    "crouch": {
        "cells": [(3, 0), (4, 0), (4, 1), (5, 0), (5, 1), (6, 1), (6, 2),
                  (6, 3), (7, 2), (7, 3), (8, 2), (8, 3)],
        "anchor": (1, 1),
    },
}


def approved_pose(rows, pose_name, head_mode="open", pupils="center",
                  tongue=False, tail_phase=0):
    """Salin template konsep lalu terapkan ekspresi tanpa mengubah siluet."""
    grid = [list(row) for row in rows]
    eyes = {
        "stand": ((7, 16), (7, 19)),
        "run": ((6, 16), (6, 19)),
        "crouch": ((7, 15), (7, 18)),
    }[pose_name]

    if head_mode in ("blink", "closed", "happy"):
        for gy, gx in eyes:
            grid[gy][gx] = "k"
    elif head_mode in ("dizzy", "dizzy2"):
        for index, (gy, gx) in enumerate(eyes):
            grid[gy][gx] = "w" if (index + (head_mode == "dizzy2")) % 2 else "n"
    elif pupils in ("left", "right", "up"):
        dx = -1 if pupils == "left" else (1 if pupils == "right" else 0)
        dy = -1 if pupils == "up" else 0
        for gy, gx in eyes:
            grid[gy][gx] = "o"
            ny, nx = gy + dy, gx + dx
            if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]):
                grid[ny][nx] = "n"

    if not tongue:
        for row in grid:
            for gx, char in enumerate(row):
                if char == "p":
                    row[gx] = "c"

    # Ganti ekor garis tipis bawaan template dengan plume tebal yang berkibas.
    spec = POSE_TAIL.get(pose_name)
    if spec:
        for gy, gx in spec["cells"]:
            if gy < len(grid) and gx < len(grid[gy]):
                grid[gy][gx] = "."
        anchor_y, anchor_x = spec["anchor"]
        plume = TAIL_PLUME[1 if tail_phase else 0]
        for ry, row in enumerate(plume):
            for rx, char in enumerate(row):
                if char == ".":
                    continue
                painted = "c" if char == "i" else char
                ny, nx = anchor_y + ry, anchor_x + rx
                if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]):
                    grid[ny][nx] = painted
    return grid


def walking_canvas(phase, head_mode="open", pupils="center", bob=0,
                   tongue=False, tail=0):
    """Empat fase langkah dengan badan stabil dan kaki independen.

    Bagian badan tetap memakai template run yang disetujui. Kaki bawaan
    dibuang lalu dipasang ulang sebagai pasangan belakang/depan: contact,
    passing, contact kebalikan, passing kebalikan. Ini membuat telapak jelas
    berpindah tanpa mengubah bentuk wajah atau membuat perut bergetar.
    """
    canvas = blank()
    x, y = 4, 5 + bob
    pose = approved_pose(
        APPROVED_RUN, "run", head_mode=head_mode, pupils=pupils,
        tongue=tongue, tail_phase=tail,
    )
    # Baris 15-17 pada template lama berisi kaki statis.
    for gy in range(15, len(pose)):
        for gx in range(len(pose[gy])):
            pose[gy][gx] = "."
    stamp(canvas, pose, x, y)

    root_y = y + 14
    gait = {
        # kaki belakang menjulur ke belakang, kaki depan ke depan
        0: ((LEG_FORWARD, 1, 0), (LEG_TUCKED, 7, 0),
            (LEG_TUCKED, 13, 0), (LEG_BACKWARD, 17, 0)),
        # pasangan jauh menapak; pasangan dekat sedang terangkat
        1: ((LEG_TUCKED, 3, -1), (LEG_STRAIGHT, 7, 0),
            (LEG_STRAIGHT, 14, 0), (LEG_TUCKED, 19, -1)),
        # ayunan berlawanan: belakang maju, depan mundur
        2: ((LEG_BACKWARD, 2, 0), (LEG_TUCKED, 7, -1),
            (LEG_FORWARD, 13, 0), (LEG_TUCKED, 18, -1)),
        # passing kebalikan sebelum kembali ke fase pertama
        3: ((LEG_STRAIGHT, 3, 0), (LEG_TUCKED, 8, -1),
            (LEG_TUCKED, 13, -1), (LEG_STRAIGHT, 18, 0)),
    }[phase]
    for leg, offset_x, offset_y in gait:
        stamp(canvas, leg, x + offset_x, root_y + offset_y)
    return canvas


# ------------------------------------------------------------- part: badan
# Torso berdiri (tanpa kaki & tanpa ekor — ekor ditempel terpisah supaya
# bisa berkibas antar frame).
TORSO_STAND = part("""
...kkkkkkkkkkkkkk......
..kooooooooooooooook....
.koooooooooooooooooook...
kooooooooooooooooooook...
koooooooooooooooooooook..
kooooooooooooooooccccook.
.kooooooooocccccccccccok..
..kookkkk........kccccok..
...kk..............kkkk...
""")

# Torso duduk: pantat di tanah, punggung melandai, dada tegak di kanan.
TORSO_SIT = part("""
............kk..
...........kook.
..........koook.
.........kkoook.
.......kkoooook.
.....kkoooooook.
...kkoooooooook.
.kkoooooooooook.
.koooooooooook..
.kooooocccook...
.koooccccccok...
.kkkkkkkkkkkk...
""")

# Badan menggantung (hold): karung kecil di bawah kepala, mengecil ke bawah.
TORSO_HANG = part("""
.kooook.
kooooook
kooooook
koooook.
.kooook.
.koook..
..kkkk..
""")

# Gelung badan tidur (kepala ditempel terpisah di kanan).
LOAF = part("""
..kkkkkkkkkkkkkk..
.koooooooooooooook
koooooooooooooooook
koooooooooooooooook
kooccoooooooccoook.
.kkkkkkkkkkkkkkkk..
""")

# Ekor runcing gaya shiba dengan ujung krem — dua fase untuk kibasan.
TAIL_UP = part("""
.kk...
kcok..
koook.
.koook
..kook
...kkk
""")

TAIL_MID = part("""
kk....
kcook.
.koook
..kkkk
""")

TAIL_SIT_A = part("""
.kkkk.
kooook
kkkkk.
""")

TAIL_SIT_B = part("""
kk....
kook..
.koook
.kkkk.
""")

TAIL_SLEEP = part("""
.kkkk.
kooook
.kkkk.
""")

TAIL_HANG = part("""
.kk
kok
kok
kk.
""")

# --------------------------------------------------------------- part: kaki
LEG_STRAIGHT = part("""
kok
kok
kok
kok
kkk
""")

LEG_FORWARD = part("""
.kok
.kok
kok.
kok.
kkk.
""")

LEG_BACKWARD = part("""
kok.
kok.
.kok
.kok
.kkk
""")

LEG_TUCKED = part("""
kok
kok
kkk
""")

LEG_REAR_STAND = part("""
koo..
koook
.koook
..kok.
..kkk.
""")

LEG_FRONT_STAND = part("""
.kok
.kok
kok.
kok.
kkk.
""")

PAW = part("""
ko
kk
""")


# --------------------------------------------------------------- part: prop
# Laptop berdiri di lantai: layar tegak di kanan, alas keyboard menapak di
# baris 25-27 (kontrak test_reference_sprites), kolom terakhir grid kosong.
LAPTOP = part("""
...kgggggk
...kgeeegk
...kgeeegk
...kgeeegk
...kgeeegk
...kgeeegk
...kgeeegk
...kgeeegk
...kgeeegk
...kgeeegk
...kgggggk
kllllllllk
kllllllllk
kkkkkkkkkk
""")

# Keyboard terpisah untuk state mengetik. Bentuknya sengaja lebar dan rendah
# supaya tetap terbaca sebagai deretan tombol pada sprite 5 px, bukan laptop
# kedua yang terpotong di sisi kanvas.
KEYBOARD = part("""
.kllllllllllk.
kllllllllllllk
kllllllllllllk
.kkkkkkkkkkkk.
""")

# Kaki depan mengetik dibuat sebagai tungkai utuh dari dada sampai telapak.
# Versi raised berhenti satu baris di atas keyboard; versi press menyentuh
# tombol. Dengan demikian telapak tidak lagi tampak melayang/terpotong.
TYPE_ARM_PRESS = part("""
kok.
kok.
.kok
.kok
..kk
..kk
""")

TYPE_ARM_RAISED = part("""
kok.
.kok
.kok
..kk
..kk
""")

MOUSE = part("""
.kk.
kllk
kllk
.kk.
""")

SMOKE_SMALL = part("""
.ss.
s..s
.ss.
""")

SMOKE_MEDIUM = part("""
..ss..ss.
.s..ss..s
s.......s
.ss...ss.
..sssss..
""")

SMOKE_LARGE = part("""
..ss....ss....
.s..s..s..ss..
s....ss....s..
.ss......ss.s.
..ssssssssss..
""")

BONE = part("""
kk...kk
kwwwwwk
kwwwwwk
kk...kk
""")

HEART_BIG = part("""
.r.r.
rrrrr
rrrrr
.rrr.
..r..
""")

HEART_SMALL = part("""
r.r
rrr
.r.
""")

DUST = part("""
d.d
.d.
""")

WAVE_SMALL = part("""
z.
.z
z.
""")

WAVE_BIG = part("""
z..
.z.
..z
.z.
z..
""")

ZZZ_SMALL = part("""
zz
.z
zz
""")

ZZZ_BIG = part("""
zzz
..z
.z.
zzz
""")


# --------------------------------------------------- perakit pose dasar
BODY_Y = 15          # baris atas torso berdiri (garis punggung)
LEG_Y = 22           # kaki berdiri: baris 22-26, telapak di 26


def stand(head_mode="open", pupils="center", legs="stand",
          bob=0, tongue=False, bark=False, tail=0):
    """Dogi dari tiga template konsep: diam, bergerak, atau merunduk."""
    gait_phases = {
        "walk_a": 0,
        "walk_mid_a": 1,
        "walk_b": 2,
        "walk_mid_b": 3,
    }
    if legs in gait_phases:
        return walking_canvas(
            gait_phases[legs], head_mode=head_mode, pupils=pupils, bob=bob,
            tongue=tongue, tail=tail,
        )

    canvas = blank()
    if legs == "splay":
        rows, pose_name, x, y = APPROVED_RUN, "run", 4, 5 + bob
    elif legs in ("tuck", "crouch"):
        rows, pose_name, x, y = APPROVED_CROUCH, "crouch", 4, 10 + bob
    else:
        rows, pose_name, x, y = APPROVED_STAND, "stand", 4, 5 + bob
    pose = approved_pose(
        rows, pose_name, head_mode=head_mode, pupils=pupils,
        tongue=tongue, tail_phase=tail,
    )
    stamp(canvas, pose, x, y)
    if bark:
        stamp(canvas, WAVE_SMALL, min(GRID_W - 2, x + len(pose[0])), y + 7)
    return canvas


def sitting(head_mode="open", pupils="center", head_dy=0, tail=0):
    """Pose rendah dari konsep ketiga, dipakai duduk/mengetik/meeting."""
    canvas = blank()
    pose = approved_pose(
        APPROVED_CROUCH, "crouch", head_mode=head_mode, pupils=pupils,
        tongue=False, tail_phase=tail,
    )
    stamp(canvas, pose, 2, 5 + head_dy)
    return canvas


def hanging(swing=0, head_mode="open"):
    """Dogi digendong dengan siluet low-pixel baru, bukan part model lama."""
    canvas = blank()
    pose = [list(row) for row in APPROVED_HOLD]
    if head_mode in ("blink", "closed"):
        pose[4][6] = "k"
        pose[4][9] = "k"
    if swing:
        # Hanya kaki bawah yang bergeser satu sel; kepala dan pegangan stabil.
        moving = []
        for gy in range(15, len(pose)):
            for gx, char in enumerate(pose[gy]):
                if char != ".":
                    moving.append((gy, gx, char))
                    pose[gy][gx] = "."
        for gy, gx, char in moving:
            nx = max(0, min(len(pose[gy]) - 1, gx + swing))
            pose[gy][nx] = char
    stamp(canvas, pose, 8, 1)
    return canvas


def keyboard_pose(paw_phase=0, key_phase=0, blush_level=0, tail=0,
                  head_mode="open"):
    """Dogi mengetik di keyboard terpisah dengan pipi makin memerah."""
    canvas = sitting(head_mode=head_mode, pupils="center", tail=tail)
    stamp(canvas, KEYBOARD, 15, 24)

    # Tombol biru bergantian tepat di bawah telapak yang sedang menekan.
    left_key = 18 + (key_phase % 2)
    right_key = 22 + ((key_phase + 1) % 2)
    patch(canvas, [(25, left_key, "b"), (25, right_key, "b")])

    # Tungkai jauh ditempel dulu, kemudian tungkai dekat. Keduanya berawal pada
    # torso baris 18 sehingga tidak ada celah transparan antara dada dan paw.
    if paw_phase == 0:
        stamp(canvas, TYPE_ARM_PRESS, 15, 18)
        stamp(canvas, TYPE_ARM_RAISED, 18, 18)
    else:
        stamp(canvas, TYPE_ARM_RAISED, 15, 18)
        stamp(canvas, TYPE_ARM_PRESS, 18, 18)

    # Pipi empat tahap: normal, hangat, merah, sangat merah. Koordinat ini
    # berada satu baris di bawah kedua mata pada template crouch.
    blush = {
        0: (),
        1: ((14, 16), (14, 20)),
        2: ((13, 16), (14, 16), (13, 20), (14, 20)),
        3: ((13, 16), (14, 16), (14, 17),
            (13, 20), (14, 20), (15, 20)),
    }[max(0, min(3, blush_level))]
    patch(canvas, [(gy, gx, "r") for gy, gx in blush])

    # Asap muncul dari sela kuping dan membesar sesuai lama mengetik. Semua
    # kepulan berhenti di atas y=5 sehingga tidak menimpa siluet kepala.
    smoke = {
        0: None,
        1: (SMOKE_SMALL, 17, 2),
        2: (SMOKE_MEDIUM, 15, 1),
        3: (SMOKE_LARGE, 10, 0),
    }[max(0, min(3, blush_level))]
    if smoke:
        art, smoke_x, smoke_y = smoke
        smoke_x += key_phase % 2
        stamp(canvas, art, smoke_x, smoke_y)
    return canvas


def laptop_pose(pupils="right", head_mode="open", scroll_phase=0,
                code_shift=0, thumb_row=None, tail=0):
    """Dogi memakai mouse; layar dan scrollbar bergerak saat scrolling."""
    canvas = sitting(head_mode=head_mode, pupils=pupils, tail=tail)
    stamp(canvas, LAPTOP, 21, 14)
    # baris kode pada layar (kolom 26-28, baris 15-23)
    code_rows = ((15, 2), (17, 3), (19, 2), (21, 3))
    for base_row, length in code_rows:
        shifted = 15 + (base_row - 15 + code_shift) % 8
        patch(canvas, [(shifted, 26 + i, "b") for i in range(length)])
    if thumb_row is not None:
        patch(canvas, [(thumb_row, 29, "r")])
    # Satu telapak menggerakkan mouse naik-turun; telapak lain diam. Ini
    # membedakan siluet scrolling dari dua telapak mengetik pada keyboard.
    stamp(canvas, MOUSE, 17, 24)
    stamp(canvas, PAW, 18, 21 + (scroll_phase % 2))
    stamp(canvas, PAW, 21, 22)
    return canvas


# --------------------------------------------------------- frame per state
def build_frames() -> dict[str, list[list[str]]]:
    frames: dict[str, list[list[str]]] = {}

    # idle: napas pelan + kedip + julur lidah
    frames["idle"] = [
        freeze(stand(tail=0)),
        freeze(stand(bob=1, tail=1)),
        freeze(stand(head_mode="blink", bob=1, tail=0)),
        freeze(stand(tongue=True, tail=1)),
    ]

    # walk: siklus kaki 4 langkah dengan goyangan badan
    frames["walk"] = [
        freeze(stand(legs="walk_a", tail=0)),
        freeze(stand(legs="walk_mid_a", bob=1, tail=1)),
        freeze(stand(legs="walk_b", tail=0)),
        freeze(stand(legs="walk_mid_b", bob=1, tail=1)),
    ]

    # chase/zoomies: langkah lebar + debu terlempar ke belakang
    chase = []
    for index, legs in enumerate(
        ("walk_a", "walk_mid_a", "walk_b", "walk_mid_b")
    ):
        canvas = stand(legs=legs, bob=index % 2, tongue=True, tail=index % 2)
        stamp(canvas, DUST, 1, 24 - (index % 2))
        chase.append(freeze(canvas))
    frames["chase"] = chase
    frames["fetch"] = chase

    # sleep: template rebah low-pixel; napas dan Zzz tetap bergerak.
    sleep = []
    for index in range(4):
        canvas = blank()
        breath = 1 if index in (1, 2) else 0
        pose = [list(row) for row in APPROVED_SLEEP]
        # Kedua mata menjadi garis tertutup, hidung tetap hitam.
        pose[4][13] = "k"
        pose[4][16] = "k"
        stamp(canvas, pose, 3, 16 - breath)
        if index in (0, 1):
            stamp(canvas, ZZZ_SMALL, 24, 9 - index)
        else:
            stamp(canvas, ZZZ_SMALL, 23, 10)
            stamp(canvas, ZZZ_BIG, 27, 5 - (index - 2))
        sleep.append(freeze(canvas))
    frames["sleep"] = sleep

    # happy: mata senang, lidah, hati naik bergantian
    happy = []
    for index in range(4):
        canvas = stand(
            head_mode="happy", bob=index % 2, tongue=True, tail=index % 2
        )
        if index % 2 == 0:
            stamp(canvas, HEART_SMALL, 8, 6)
            stamp(canvas, HEART_BIG, 12, 2)
        else:
            stamp(canvas, HEART_BIG, 7, 3)
            stamp(canvas, HEART_SMALL, 13, 7)
        happy.append(freeze(canvas))
    frames["happy"] = happy

    # friend_play: membungkuk mengajak main lalu melompat kecil. Dua jendela
    # Dogi saling menghadap sehingga pose ini terbaca sebagai permainan.
    friend_play = []
    for index, legs in enumerate(("crouch", "splay", "crouch", "tuck")):
        canvas = stand(
            legs=legs,
            head_mode="happy",
            tongue=True,
            bob=1 if index in (0, 2) else 0,
            tail=index % 2,
        )
        if index in (1, 3):
            stamp(canvas, DUST, 2, 25)
        # Hati kecil melompat mengikuti fase agar keempat frame tetap unik.
        stamp(canvas, HEART_SMALL, 25 - index, 4 + index)
        friend_play.append(freeze(canvas))
    frames["friend_play"] = friend_play

    # friend_tussle: adu dorong kartun tanpa ekspresi marah atau luka. Debu
    # dan gonggongan kecil memberi rasa ramai, sementara mata tetap senang.
    friend_tussle = []
    for index, legs in enumerate(("splay", "crouch", "splay", "tuck")):
        canvas = stand(
            legs=legs,
            head_mode="happy",
            tongue=index % 2 == 0,
            bark=index in (0, 2),
            bob=index % 2,
            tail=index % 2,
        )
        stamp(canvas, DUST, 2 + index * 2, 24 - index % 2)
        if index in (0, 2):
            stamp(canvas, WAVE_SMALL, 29, 8)
        friend_tussle.append(freeze(canvas))
    frames["friend_tussle"] = friend_tussle

    # wait_food: Dogi duduk menatap tulang yang masih dipegang. Ekor runcing
    # berkibas dan setitik air liur turun perlahan sebelum siklus diulang.
    wait_food = []
    drool_cells = (
        ((16, 24, "z"),),
        ((16, 24, "z"), (17, 24, "z")),
        ((17, 24, "z"), (18, 24, "z")),
        (),
    )
    for index in range(4):
        canvas = sitting(
            head_mode="blink" if index == 3 else "open",
            pupils="up",
            tail=index % 2,
        )
        patch(canvas, list(drool_cells[index]))
        wait_food.append(freeze(canvas))
    frames["wait_food"] = wait_food

    # dig: kaki depan mengais bergantian, debu terbang
    dig = []
    for index in range(4):
        canvas = stand(
            bob=1, pupils="up" if index < 2 else "center", tail=index % 2
        )
        if index % 2 == 0:
            stamp(canvas, DUST, 23, 23)
            stamp(canvas, DUST, 25, 25)
        else:
            stamp(canvas, DUST, 24, 21)
            stamp(canvas, DUST, 26, 24)
        dig.append(freeze(canvas))
    # kais: timpa kaki depan-dekat dengan pose maju/terlipat bergantian
    for index, canvas_rows in enumerate(dig):
        grid = [list(row) for row in canvas_rows]
        for gy in range(LEG_Y, GRID_H):
            for gx in (19, 20, 21, 22):
                grid[gy][gx] = "."
        if index % 2 == 0:
            stamp(grid, LEG_FORWARD, 19, LEG_Y)
        else:
            stamp(grid, LEG_TUCKED, 20, LEG_Y + 2)
        dig[index] = freeze(grid)
    frames["dig"] = dig

    # eat: tulang menempel di mulut, kepala mengunyah naik-turun
    eat = []
    for index in range(4):
        drop = 1 if index % 2 else 0
        canvas = stand(
            head_mode="blink" if index == 3 else "open",
            bob=drop,
            tail=index % 2,
        )
        stamp(canvas, BONE, 24, 11 + drop)
        eat.append(freeze(canvas))
    frames["eat"] = eat

    # hold: menggantung kaget, kaki dan ekor mengayun
    frames["hold"] = [
        freeze(hanging(swing=0)),
        freeze(hanging(swing=1)),
        freeze(hanging(swing=0, head_mode="blink")),
        freeze(hanging(swing=-1)),
    ]

    # type: empat tahap lelah x empat fase tombol. Runtime memilih kelompok
    # tahap berdasarkan berapa lama pengguna terus mengetik.
    frames["type"] = [
        freeze(keyboard_pose(
            paw_phase=phase % 2,
            key_phase=phase,
            blush_level=heat,
            head_mode="blink" if phase == 3 and heat >= 2 else "open",
            tail=phase % 2,
        ))
        for heat in range(4)
        for phase in range(4)
    ]

    # scroll: penanda 'r' merambat di bezel layar, konten ikut bergeser
    for state, thumb_rows in (("scroll_up", (21, 19, 17, 15)),
                              ("scroll_down", (15, 17, 19, 21))):
        direction = -1 if state == "scroll_up" else 1
        frames[state] = [
            freeze(laptop_pose(scroll_phase=index % 2,
                               code_shift=(-direction * index) % 8,
                               thumb_row=thumb_rows[index],
                               tail=index % 2))
            for index in range(4)
        ]

    # meeting_alert: gonggong waspada + gelombang suara membesar
    alert = []
    for index in range(4):
        bark_now = index % 2 == 0
        canvas = stand(
            bark=bark_now, bob=0 if bark_now else 1, tail=index % 2
        )
        if bark_now:
            stamp(canvas, WAVE_SMALL, 30, 8)
        else:
            stamp(canvas, WAVE_BIG, 29, 6)
        alert.append(freeze(canvas))
    frames["meeting_alert"] = alert

    # meeting_watch: duduk tenang menatap, kedip sesekali
    frames["meeting_watch"] = [
        freeze(sitting(pupils="right", tail=0)),
        freeze(sitting(pupils="right", head_dy=1, tail=1)),
        freeze(sitting(head_mode="blink", pupils="right", head_dy=1, tail=0)),
        freeze(sitting(pupils="right", tail=1)),
    ]

    # think: melirik kiri-atas-kanan (aplikasi memutarnya ping-pong)
    frames["think"] = [
        freeze(stand(pupils="left", tail=0)),
        freeze(stand(pupils="up", tail=1)),
        freeze(stand(pupils="right", tail=0)),
        freeze(stand(pupils="up", bob=1, tail=1)),
    ]

    # Kibasan khusus: badan tenang, ekor runcing berganti posisi setiap frame.
    frames["tail_wag"] = [
        freeze(stand(tail=0)),
        freeze(stand(tail=1, bob=1)),
        freeze(stand(tail=0, tongue=True)),
        freeze(stand(tail=1)),
    ]

    # jump: jongkok -> melesat -> puncak -> mendarat
    jump = []
    jump.append(freeze(stand(legs="crouch", bob=2, tail=0)))
    jump.append(freeze(stand(
        legs="splay", head_mode="happy", tongue=True, tail=1
    )))
    jump.append(freeze(stand(
        legs="tuck", head_mode="happy", tongue=True, tail=0
    )))
    landing = stand(legs="splay", bob=1, tail=1)
    stamp(landing, DUST, 2, 25)
    stamp(landing, DUST, 25, 25)
    jump.append(freeze(landing))
    frames["jump"] = jump

    # dizzy: badan oleng + mata spiral + percikan di atas kepala
    dizzy = []
    for index in range(4):
        mode = "dizzy" if index % 2 == 0 else "dizzy2"
        offset = (0, 1, 0, -1)[index]
        canvas = stand(head_mode=mode, bob=index % 2, tail=index % 2)
        patch(canvas, [(1, 17 + offset, "z"), (0, 21, "z"),
                       (1, 25 - offset, "z")])
        dizzy.append(freeze(canvas))
    frames["dizzy"] = dizzy

    # pee: Dogi jongkok (pose crouch) sambil pipis; genangan kuning membesar
    # di bawah pantat dengan sedikit tetesan agar jelas terbaca.
    pee = []
    puddle_w = [0, 4, 7, 10]
    for index in range(4):
        canvas = sitting(
            head_mode="blink" if index == 3 else "open",
            pupils="left",
            tail=index % 2,
        )
        base_x, base_y = 3, GRID_H - 1
        stream_x = base_x + 3
        # pancuran kecil dari bawah pantat menuju genangan
        if index in (1, 2):
            for gy in range(GRID_H - 5, base_y):
                patch(canvas, [(gy, stream_x, "y")])
        width = puddle_w[index]
        if width:
            patch(canvas, [(base_y, base_x + i, "y") for i in range(width)])
            patch(canvas, [(base_y - 1, base_x + 1 + i, "y")
                           for i in range(max(0, width - 3))])
        pee.append(freeze(canvas))
    frames["pee"] = pee

    return frames


# ------------------------------------------------------------------ render
def render(rows: list[str], palette: dict[str, str]) -> Image.Image:
    image = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    pixels = image.load()
    for gy, row in enumerate(rows):
        for gx, char in enumerate(row):
            if char == ".":
                continue
            color = palette[char]
            value = tuple(int(color.lstrip("#")[i:i + 2], 16)
                          for i in (0, 2, 4)) + (255,)
            for py in range(BLOCK):
                for px in range(BLOCK):
                    pixels[gx * BLOCK + px, gy * BLOCK + py] = value
    return image


def main() -> None:
    frames = build_frames()
    expected = {
        "idle": 4, "walk": 4, "chase": 4, "fetch": 4, "sleep": 4,
        "happy": 4, "friend_play": 4, "friend_tussle": 4,
        "wait_food": 4, "dig": 4, "eat": 4, "hold": 4, "type": 16,
        "scroll_up": 4, "scroll_down": 4, "meeting_alert": 4,
        "meeting_watch": 4, "think": 4, "tail_wag": 4,
        "jump": 4, "dizzy": 4, "pee": 4,
    }
    assert set(frames) == set(expected)
    for state, count in expected.items():
        assert len(frames[state]) == count, (state, len(frames[state]))

    for old_sprite in OUTPUT.rglob("*.png"):
        old_sprite.unlink()
    total = 0
    for theme, theme_palette in THEMES.items():
        palette = dict(FIXED)
        palette.update(theme_palette)
        theme_dir = OUTPUT / theme.lower()
        theme_dir.mkdir(parents=True, exist_ok=True)
        for state, state_frames in frames.items():
            for index, rows in enumerate(state_frames):
                image = render(rows, palette)
                image.save(theme_dir / f"{state}_{index}.png", optimize=True)
                image.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(
                    theme_dir / f"{state}_{index}_left.png", optimize=True
                )
                total += 2

    # contact sheet QA (tema Shiba)
    palette = dict(FIXED)
    palette.update(THEMES["Shiba"])
    states = list(expected)
    columns = max(expected.values())
    sheet = Image.new(
        "RGBA", (FRAME_SIZE[0] * columns, FRAME_SIZE[1] * len(states)),
        (24, 24, 24, 255),
    )
    for row, state in enumerate(states):
        for column, rows in enumerate(frames[state]):
            sheet.alpha_composite(
                render(rows, palette),
                (column * FRAME_SIZE[0], row * FRAME_SIZE[1]),
            )
    sheet_path = ROOT / "qa" / "handmade-sprites.png"
    sheet.save(sheet_path)

    # Ringkasan satu frame per state untuk audit cepat konsistensi karakter.
    preview_columns = 6
    preview_rows = (len(states) + preview_columns - 1) // preview_columns
    preview = Image.new(
        "RGBA",
        (FRAME_SIZE[0] * preview_columns, FRAME_SIZE[1] * preview_rows),
        (24, 24, 24, 255),
    )
    for index, state in enumerate(states):
        preview.alpha_composite(
            render(frames[state][0], palette),
            ((index % preview_columns) * FRAME_SIZE[0],
             (index // preview_columns) * FRAME_SIZE[1]),
        )
    preview_path = ROOT / "qa" / "all-states-preview.png"
    preview.save(preview_path)
    print(f"{total} sprite ditulis ke {OUTPUT}")
    print(f"Contact sheet: {sheet_path}")
    print(f"All states: {preview_path}")


if __name__ == "__main__":
    main()
