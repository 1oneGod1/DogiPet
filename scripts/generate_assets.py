"""Buat ikon aplikasi dari sprite Dogi yang sama dengan aplikasi."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dogi import COLOR_THEMES, FIXED_COLORS, IDLE_1  # noqa: E402
from version import VERSION  # noqa: E402


def main() -> None:
    canvas_size = 512
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    approved_sprite = ROOT / "assets" / "sprites" / "shiba" / "idle_0.png"
    if approved_sprite.exists():
        sprite = Image.open(approved_sprite).convert("RGBA")
        bbox = sprite.getbbox()
        sprite = sprite.crop(bbox) if bbox else sprite
        sprite = sprite.resize((384, 300), Image.Resampling.NEAREST)
        image.alpha_composite(sprite, ((canvas_size - 384) // 2, 106))
    else:
        scale = 24
        frame = IDLE_1
        width = len(frame[0]) * scale
        height = len(frame) * scale
        offset_x = (canvas_size - width) // 2
        offset_y = (canvas_size - height) // 2
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

    version_parts = [int(part) for part in VERSION.split(".")]
    version_parts.extend([0] * (4 - len(version_parts)))
    version_tuple = tuple(version_parts[:4])
    (assets / "version_info.txt").write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '1oneGod1'),
        StringStruct('FileDescription', 'DogiPet Desktop Companion'),
        StringStruct('FileVersion', '{VERSION}'),
        StringStruct('InternalName', 'DogiPet'),
        StringStruct('OriginalFilename', 'DogiPet.exe'),
        StringStruct('ProductName', 'DogiPet'),
        StringStruct('ProductVersion', '{VERSION}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
