"""Pasang/lepas hook Claude Code untuk DogiPet.

Menulis hook ke ~/.claude/settings.json agar Claude Code memberi tahu Dogi
saat agent mulai bekerja (UserPromptSubmit) dan saat selesai (Stop). Entri
milik DogiPet dikenali dari perintahnya, sehingga bisa dilepas kembali tanpa
mengusik hook lain milik pengguna.
"""

from __future__ import annotations

import json
import pathlib
import sys

SETTINGS_FILE = pathlib.Path.home() / ".claude" / "settings.json"

# event Claude Code -> status yang dikirim ke Dogi
HOOK_EVENTS = {
    "UserPromptSubmit": "thinking",
    "Stop": "done",
}


class HookError(RuntimeError):
    """Kesalahan yang aman ditampilkan kepada pengguna."""


def hook_command(status: str) -> str:
    """Perintah yang dijalankan Claude Code untuk mengirim status ke Dogi."""
    executable = pathlib.Path(sys.executable)
    if getattr(sys, "frozen", False):
        return f'"{executable}" --hook {status}'
    script = pathlib.Path(__file__).resolve().parent / "dogi_hook.py"
    return f'"{executable}" "{script}" {status}'


def _is_dogi_command(command: object) -> bool:
    if not isinstance(command, str):
        return False
    lowered = command.lower()
    return "dogi_hook.py" in lowered or (
        "dogipet" in lowered and "--hook" in lowered
    )


def _is_dogi_group(group: object) -> bool:
    if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
        return False
    return any(
        isinstance(item, dict) and _is_dogi_command(item.get("command"))
        for item in group["hooks"]
    )


def _strip_dogi(hook_config: dict) -> tuple[dict, bool]:
    """Buang entri DogiPet dari konfigurasi hooks; sisanya dibiarkan utuh."""
    changed = False
    result: dict = {}
    for event, groups in hook_config.items():
        if not isinstance(groups, list):
            result[event] = groups
            continue
        kept_groups = []
        for group in groups:
            if isinstance(group, dict) and isinstance(group.get("hooks"), list):
                kept_hooks = [
                    item
                    for item in group["hooks"]
                    if not (
                        isinstance(item, dict)
                        and _is_dogi_command(item.get("command"))
                    )
                ]
                if len(kept_hooks) != len(group["hooks"]):
                    changed = True
                    if not kept_hooks:
                        continue
                    group = {**group, "hooks": kept_hooks}
            kept_groups.append(group)
        if kept_groups or not groups:
            result[event] = kept_groups
    return result, changed


def _load_settings(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HookError(
            f"Tidak bisa membaca {path.name}: {exc}. "
            "Periksa file pengaturan Claude Code-mu."
        ) from exc
    if not isinstance(data, dict):
        raise HookError(f"Format {path.name} tidak dikenali (bukan objek JSON).")
    return data


def _save_settings(path: pathlib.Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".dogipet.tmp")
        temporary.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as exc:
        raise HookError(f"Gagal menulis {path}: {exc}") from exc


def is_installed(path: pathlib.Path | None = None) -> bool:
    path = path or SETTINGS_FILE
    try:
        settings = _load_settings(path)
    except HookError:
        return False
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    return all(
        isinstance(hooks.get(event), list)
        and any(_is_dogi_group(group) for group in hooks[event])
        for event in HOOK_EVENTS
    )


def install(path: pathlib.Path | None = None) -> None:
    """Pasang hook thinking/done; entri lama DogiPet diganti yang baru."""
    path = path or SETTINGS_FILE
    settings = _load_settings(path)
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
    hooks, _ = _strip_dogi(hooks)
    for event, status in HOOK_EVENTS.items():
        groups = hooks.setdefault(event, [])
        groups.append(
            {"hooks": [{"type": "command", "command": hook_command(status)}]}
        )
    settings["hooks"] = hooks
    _save_settings(path, settings)


def uninstall(path: pathlib.Path | None = None) -> None:
    path = path or SETTINGS_FILE
    if not path.exists():
        return
    settings = _load_settings(path)
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return
    stripped, changed = _strip_dogi(hooks)
    if not changed:
        return
    if stripped:
        settings["hooks"] = stripped
    else:
        settings.pop("hooks", None)
    _save_settings(path, settings)
