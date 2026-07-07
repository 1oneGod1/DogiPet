"""Tulis metadata build yang akan dibundel PyInstaller."""

import argparse
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--timestamp")
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).isoformat()
    root = Path(__file__).resolve().parents[1]
    (root / "build_info.py").write_text(
        '"""Metadata build yang dibuat otomatis."""\n\n'
        f'BUILD_ID = "{args.build_id}"\n'
        f'BUILD_TIMESTAMP = "{timestamp}"\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
