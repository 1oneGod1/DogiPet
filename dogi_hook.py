"""
dogi_hook.py — jembatan antara Claude Code dan Dogi.

Dipanggil oleh Claude Code hooks untuk menulis status agent ke
~/.dogi/agent_status.json, yang dipantau oleh dogi.py.

Pemakaian:
    python dogi_hook.py thinking   # agent mulai bekerja
    python dogi_hook.py done       # agent selesai
"""

import json
import pathlib
import sys
import time

status = sys.argv[1].lower() if len(sys.argv) > 1 else "done"
if status not in {"thinking", "done"}:
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
