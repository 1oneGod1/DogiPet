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
LOGICAL_FRAME_SIZE = (32, 28)

STATE_MAX_CONTENT = {
    "idle": (80, 60),
    "walk": (85, 60),
    "chase": (95, 55),
    "fetch": (95, 55),
    "sleep": (85, 50),
    "happy": (70, 70),
    "dig": (80, 65),
    "eat": (100, 65),
    "hold": (55, 120),
    "type": (120, 72),
    "scroll_up": (120, 80),
    "scroll_down": (120, 80),
    "meeting_alert": (120, 80),
    "meeting_watch": (120, 70),
    "think": (75, 85),
    "jump": (95, 65),
    "dizzy": (80, 90),
}

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
    "idle": (25, 122),
    "walk": (145, 245),
    "chase": (270, 365),
    "happy": (382, 483),
    "sleep": (493, 602),
    "eat": (623, 727),
    "dig": (748, 846),
    "hold": (846, 1000),
    "type": (1013, 1107),
    "scroll_up": (1121, 1221),
    "scroll_down": (1238, 1331),
    "meeting_alert": (1345, 1456),
    "meeting_watch": (1467, 1554),
    "think": (1559, 1674),
    "jump": (1683, 1790),
    "dizzy": (1800, 1924),
    # Sheet v0.5.1 dedicates its final row to dizzy; fetch reuses the clean
    # sprint cycle, which is the same motion used while chasing a bone.
    "fetch": (270, 365),
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


def clean_chroma_residue(image: Image.Image) -> Image.Image:
    """Harden alpha and discard any green-key fringe left by generation."""
    out = Image.new("RGBA", image.size)
    pixels = []
    for red, green, blue, alpha in _pixels(image.convert("RGBA")):
        green_key = green > 120 and green > red * 1.35 and green > blue * 1.35
        if alpha < 128 or green_key:
            pixels.append((0, 0, 0, 0))
        else:
            pixels.append((red, green, blue, 255))
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


def normalize_frame(content: Image.Image, state: str) -> Image.Image:
    max_width, max_height = STATE_MAX_CONTENT[state]
    ratio = min(max_width / content.width, max_height / content.height)
    content = content.resize(
        (max(1, round(content.width * ratio)), max(1, round(content.height * ratio))),
        Image.Resampling.NEAREST,
    )
    frame = Image.new("RGBA", FRAME_SIZE)
    x = (FRAME_SIZE[0] - content.width) // 2
    y = FRAME_SIZE[1] - content.height - 3
    frame.alpha_composite(content, (x, y))
        # Match the original Dogi renderer exactly: a 32×28 logical canvas,
        # enlarged in hard 5×5 blocks. This prevents "fine" pixel art from
        # sneaking back in through generated source assets.
    frame = frame.resize(LOGICAL_FRAME_SIZE, Image.Resampling.NEAREST)
    return frame.resize(FRAME_SIZE, Image.Resampling.NEAREST)


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
        frames.append(normalize_frame(cell.crop(bbox), state))
    return frames


def extract_typing_frames(sheet: Image.Image) -> list[Image.Image]:
    """Import seven transitions plus frame zero as a seamless loop close."""
    cleaned = clean_chroma_residue(sheet.convert("RGBA"))
    frames = []
    for source_index in (0, 1, 2, 3, 4, 5, 6, 0):
        left = round(source_index * cleaned.width / 8)
        right = round((source_index + 1) * cleaned.width / 8)
        cell = cleaned.crop((left, 0, right, cleaned.height))
        bbox = cell.getbbox()
        if not bbox:
            raise RuntimeError(f"No visible pixels for typing frame {source_index}")
        frames.append(normalize_frame(cell.crop(bbox), "type"))
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
    parser.add_argument(
        "--typing-strip",
        type=Path,
        default=ROOT / "assets" / "reference" / "dogi-typing-strip-v053.png",
    )
    args = parser.parse_args()
    if not args.source.exists():
        raise SystemExit(f"Reference sheet not found: {args.source}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(args.source)
    cleaned = source.convert("RGBA") if "A" in source.getbands() else remove_checkerboard(source)
    cleaned = clean_chroma_residue(cleaned)
    for old_sprite in OUTPUT.rglob("*.png"):
        old_sprite.unlink()
    base_frames = {
        state: extract_frames(cleaned, state)
        for state in ROWS
    }
    if args.typing_strip.exists():
        base_frames["type"] = extract_typing_frames(Image.open(args.typing_strip))

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
