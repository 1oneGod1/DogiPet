# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

root = Path(SPECPATH)
sprite_datas = [
    (str(path), str(path.parent.relative_to(root)))
    for path in (root / "assets" / "sprites").rglob("*.png")
]

a = Analysis(
    [str(root / "dogi.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "assets" / "dogipet.png"), "assets")] + sprite_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DogiPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(root / "assets" / "dogipet.ico")],
    version=str(root / "assets" / "version_info.txt"),
)
