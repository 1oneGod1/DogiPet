"""Buat manifest kecil yang dibaca updater DogiPet."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--channel", choices=("stable", "continuous"), required=True)
    parser.add_argument("--output", default="release/build-info.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "version": args.version.lstrip("v"),
                "build_id": args.build_id,
                "channel": args.channel,
                "installer_asset": "DogiPet-Setup.exe",
                "checksum_asset": "DogiPet-Setup.exe.sha256",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
