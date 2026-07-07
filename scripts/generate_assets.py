"""Buat ikon aplikasi dari sprite Dogi yang sama dengan aplikasi."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dogi import COLOR_THEMES, FIXED_COLORS, IDLE_1  # noqa: E402


def main() -> None:
    canvas_size = 512
    scale = 24
    frame = IDLE_1
    width = len(frame[0]) * scale
    height = len(frame) * scale
    offset_x = (canvas_size - width) // 2
    offset_y = (canvas_size - height) // 2
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    palette = dict(FIXED_COLORS)
    palette.update(COLOR_THEMES["Shiba"])
    for y, row in enumerate(frame):
        for x, key in enumerate(row):
            color = palette.get(key)
            if color:
                draw.rectangle(
                    (
                        offset_x + x * scale,
                        offset_y + y * scale,
                        offset_x + (x + 1) * scale - 1,
                        offset_y + (y + 1) * scale - 1,
                    ),
                    fill=color,
                )

    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    image.save(assets / "dogipet.png")
    image.save(
        assets / "dogipet.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
