"""Import the clean approved Dogi contact sheet into app-ready sprites.

The importer accepts the recreated alpha sheet (or the older RGB checkerboard
reference as a fallback), extracts and aligns every cell, and creates all six
DogiPet colour themes without changing props such as laptops or bowls.
"""

from __future__ import annotations

import argparse
import colorsys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "sprites"
FRAME_SIZE = (160, 140)

THEMES = {
    "Shiba": {"body": "#e8a44c", "cream": "#f6ddb0", "outline": "#5a3a21"},
    "Husky": {"body": "#9aa7b5", "cream": "#f2f2f2", "outline": "#3d4653"},
    "Coklat": {"body": "#8a5a33", "cream": "#c99a6b", "outline": "#4a2d14"},
    "Hitam": {"body": "#454545", "cream": "#9a9a9a", "outline": "#141414"},
    "Golden": {"body": "#e6c46a", "cream": "#f7ecc7", "outline": "#7a5a1f"},
    "Putih": {"body": "#f4f0e6", "cream": "#ffffff", "outline": "#9a938a"},
}

# Clean ImageGen sheet layout: four columns and seventeen rows.
ROWS = {
    "idle": 0,
    "walk": 1,
    "chase": 2,
    "happy": 3,
    "sleep": 4,
    "eat": 5,
    "dig": 6,
    "hold": 7,
    "type": 8,
    "scroll_up": 9,
    "scroll_down": 10,
    "meeting_alert": 11,
    "meeting_watch": 12,
    "think": 13,
    "jump": 14,
    "dizzy": 15,
    "fetch": 16,
}
GRID_COLUMNS = 4
ROW_RANGES = {
    "idle": (24, 114),
    "walk": (147, 237),
    "chase": (264, 353),
    "happy": (366, 463),
    "sleep": (482, 582),
    "eat": (607, 699),
    "dig": (723, 815),
    "hold": (829, 974),
    "type": (981, 1071),
    "scroll_up": (1090, 1172),
    "scroll_down": (1194, 1280),
    "meeting_alert": (1293, 1396),
    "meeting_watch": (1407, 1501),
    "think": (1502, 1597),
    "jump": (1605, 1715),
    "dizzy": (1717, 1817),
    "fetch": (1824, 1914),
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _pixels(image: Image.Image):
    getter = getattr(image, "get_flattened_data", None)
    return getter() if getter else image.getdata()


def remove_checkerboard(image: Image.Image) -> Image.Image:
    """Convert the baked white/grey checkerboard into hard transparency."""
    source = image.convert("RGB")
    out = Image.new("RGBA", source.size)
    pixels = []
    for red, green, blue in _pixels(source):
        spread = max(red, green, blue) - min(red, green, blue)
        # The sheet background is neutral and brighter than every useful prop.
        alpha = 0 if min(red, green, blue) > 230 and spread < 14 else 255
        pixels.append((red, green, blue, alpha))
    out.putdata(pixels)
    return out


def recolor_dog(image: Image.Image, palette: dict[str, str]) -> Image.Image:
    """Recolour warm-brown fur while preserving facial details and props."""
    body = _rgb(palette["body"])
    cream = _rgb(palette["cream"])
    outline = _rgb(palette["outline"])
    out = Image.new("RGBA", image.size)
    result = []
    for red, green, blue, alpha in _pixels(image):
        if not alpha:
            result.append((0, 0, 0, 0))
            continue
        hue, saturation, value = colorsys.rgb_to_hsv(
            red / 255.0, green / 255.0, blue / 255.0
        )
        warm_brown = (hue <= 0.16 or hue >= 0.96) and saturation >= 0.22
        # Pink tongues are redder and brighter; leave them untouched.
        tongue = red > 155 and red > green * 1.35 and blue > 55
        if warm_brown and not tongue:
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            if luminance < 82:
                mapped = outline
            elif luminance > 174:
                mapped = cream
            else:
                mapped = body
            result.append((*mapped, 255))
        else:
            result.append((red, green, blue, 255))
    out.putdata(result)
    return out


def extract_frames(sheet: Image.Image, state: str) -> list[Image.Image]:
    top, bottom = ROW_RANGES[state]
    frames = []
    for index in range(GRID_COLUMNS):
        left = round(index * sheet.width / GRID_COLUMNS)
        right = round((index + 1) * sheet.width / GRID_COLUMNS)
        cell = sheet.crop((left, top, right, bottom))
        bbox = cell.getbbox()
        if not bbox:
            raise RuntimeError(f"No visible pixels for {state} frame {index}")
        content = cell.crop(bbox)
        if content.width > FRAME_SIZE[0] - 8 or content.height > FRAME_SIZE[1] - 6:
            ratio = min(
                (FRAME_SIZE[0] - 8) / content.width,
                (FRAME_SIZE[1] - 6) / content.height,
            )
            content = content.resize(
                (round(content.width * ratio), round(content.height * ratio)),
                Image.Resampling.NEAREST,
            )
        frame = Image.new("RGBA", FRAME_SIZE)
        x = (FRAME_SIZE[0] - content.width) // 2
        y = FRAME_SIZE[1] - content.height - 3
        frame.alpha_composite(content, (x, y))
        frames.append(frame)
    return frames


def mirror_frame(image: Image.Image) -> Image.Image:
    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def build_preview(frames: dict[str, list[Image.Image]], target: Path) -> None:
    states = list(ROWS)
    preview = Image.new("RGBA", (FRAME_SIZE[0] * 4, FRAME_SIZE[1] * len(states)))
    for row, state in enumerate(states):
        for column, frame in enumerate(frames[state][:4]):
            preview.alpha_composite(frame, (column * FRAME_SIZE[0], row * FRAME_SIZE[1]))
    preview.save(target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    if not args.source.exists():
        raise SystemExit(f"Reference sheet not found: {args.source}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(args.source)
    cleaned = source.convert("RGBA") if "A" in source.getbands() else remove_checkerboard(source)
    for old_sprite in OUTPUT.rglob("*.png"):
        old_sprite.unlink()
    base_frames = {
        state: extract_frames(cleaned, state)
        for state in ROWS
    }

    for theme, palette in THEMES.items():
        theme_dir = OUTPUT / theme.lower()
        theme_dir.mkdir(parents=True, exist_ok=True)
        for state, frames in base_frames.items():
            for index, frame in enumerate(frames):
                themed = recolor_dog(frame, palette)
                themed.save(theme_dir / f"{state}_{index}.png", optimize=True)
                mirror_frame(themed).save(
                    theme_dir / f"{state}_{index}_left.png", optimize=True
                )

    build_preview(
        {state: [recolor_dog(frame, THEMES["Coklat"]) for frame in frames]
         for state, frames in base_frames.items()},
        ROOT / "qa" / "reference-sprites-imported.png",
    )
    print(f"Imported {sum(len(frames) for frames in base_frames.values())} clean frames")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
