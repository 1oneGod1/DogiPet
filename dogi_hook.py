"""
dogi_hook.py — jembatan antara Claude Code dan Dogi.

Dipanggil oleh Claude Code hooks untuk menulis status agent ke
~/.dogi/agent_status.json, yang dipantau oleh dogi.py. Hook bisa dipasang
otomatis dari Control Center DogiPet (halaman Agent AI) atau manual:

    python dogi_hook.py thinking   # agent mulai bekerja
    python dogi_hook.py done       # agent selesai
"""

import json
import pathlib
import sys
import time

VALID_STATUSES = {"thinking", "done"}


def write_status(status="done"):
    """Tulis status agent secara atomik agar dogi.py tidak membaca file separuh."""
    status = str(status).lower()
    if status not in VALID_STATUSES:
        raise SystemExit("Status harus 'thinking' atau 'done'.")
    conf_dir = pathlib.Path.home() / ".dogi"
    conf_dir.mkdir(exist_ok=True)
    status_file = conf_dir / "agent_status.json"
    temporary = status_file.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"status": status, "ts": time.time()}),
        encoding="utf-8",
    )
    temporary.replace(status_file)


if __name__ == "__main__":
    write_status(sys.argv[1] if len(sys.argv) > 1 else "done")
