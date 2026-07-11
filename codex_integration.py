"""Jembatan aman antara DogiPet dan Codex CLI resmi.

DogiPet tidak pernah membaca cache login atau token Codex. Seluruh autentikasi
dan pemanggilan model ditangani executable ``codex`` yang dipasang pengguna.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


CODEX_INSTALL_URL = "https://developers.openai.com/codex/cli"
CODEX_AUTH_URL = "https://developers.openai.com/codex/auth"
CODEX_TIMEOUT_SECONDS = 15 * 60


class CodexIntegrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class CodexStatus:
    available: bool
    authenticated: bool
    detail: str
    executable: Path | None = None


def _candidate_paths():
    configured = os.environ.get("DOGIPET_CODEX_CLI", "").strip()
    if configured:
        yield Path(configured).expanduser()

    for name in ("codex.exe", "codex.cmd", "codex"):
        found = shutil.which(name)
        if found:
            yield Path(found)

    appdata = os.environ.get("APPDATA")
    if appdata:
        yield Path(appdata) / "npm" / "codex.cmd"


def _command(executable: Path, *args: str) -> list[str]:
    if os.name == "nt" and executable.suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(executable), *args]
    return [str(executable), *args]


def _run(executable: Path, *args: str, **kwargs) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    return subprocess.run(
        _command(executable, *args),
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        **kwargs,
    )


def find_codex_cli() -> Path | None:
    """Cari Codex CLI yang benar-benar dapat dijalankan.

    Windows App Execution Alias kadang terlihat di PATH tetapi menolak proses
    desktop lain. Karena itu setiap kandidat diprobe, bukan sekadar ditemukan.
    """
    seen = set()
    for raw in _candidate_paths():
        path = raw.resolve(strict=False)
        key = os.path.normcase(str(path))
        if key in seen or not path.exists():
            continue
        seen.add(key)
        try:
            result = _run(
                path,
                "--version",
                capture_output=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            return path
    return None


def codex_status() -> CodexStatus:
    executable = find_codex_cli()
    if executable is None:
        return CodexStatus(
            False,
            False,
            "CODEX CLI BELUM TERPASANG ATAU TIDAK DAPAT DIJALANKAN",
        )
    try:
        result = _run(
            executable,
            "login",
            "status",
            capture_output=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CodexStatus(True, False, f"STATUS CODEX GAGAL: {exc}", executable)
    detail = (result.stdout or result.stderr or "").strip()
    if result.returncode == 0:
        return CodexStatus(True, True, "AKUN CODEX TERHUBUNG", executable)
    return CodexStatus(
        True,
        False,
        detail[:180] or "CODEX CLI BELUM LOGIN",
        executable,
    )


def start_codex_login() -> Path:
    """Buka alur login resmi Codex di console/browser terpisah."""
    executable = find_codex_cli()
    if executable is None:
        raise CodexIntegrationError(
            "Codex CLI belum terpasang atau alias Windows tidak dapat dijalankan."
        )
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if os.name == "nt" else 0
    try:
        subprocess.Popen(
            _command(executable, "login"),
            creationflags=flags,
            close_fds=os.name != "nt",
        )
    except OSError as exc:
        raise CodexIntegrationError(f"Tidak dapat membuka login Codex: {exc}") from exc
    return executable


def create_minutes_with_codex(
    transcript: str,
    *,
    timeout: int = CODEX_TIMEOUT_SECONDS,
    executable: Path | None = None,
) -> str:
    """Kirim transkrip melalui stdin ke ``codex exec`` dan ambil jawaban akhir."""
    text = str(transcript or "").strip()
    if not text:
        raise CodexIntegrationError("Transkrip rapat masih kosong.")
    executable = executable or find_codex_cli()
    if executable is None:
        raise CodexIntegrationError("Codex CLI belum tersedia.")

    instruction = (
        "Buat notulen rapat profesional dalam Bahasa Indonesia hanya dari "
        "transkrip pada stdin. Jangan mengarang. Gunakan Markdown dengan bagian: "
        "Ringkasan eksekutif, Topik yang dibahas, Keputusan, Action items berupa "
        "checkbox beserta PIC dan tenggat bila disebut, Risiko/kendala, dan "
        "Pertanyaan terbuka. Pertahankan nama, angka, tanggal, serta timestamp. "
        "Jika informasi tidak ada, tulis 'Tidak disebutkan'. Keluarkan hanya "
        "notulen akhir, tanpa penjelasan proses. Jangan membaca atau mengubah file."
    )
    try:
        with tempfile.TemporaryDirectory(prefix="dogipet-codex-") as temp:
            result = _run(
                executable,
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                instruction,
                input=text,
                capture_output=True,
                timeout=timeout,
                cwd=temp,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise CodexIntegrationError("Codex terlalu lama membuat notulen.") from exc
    except OSError as exc:
        raise CodexIntegrationError(f"Codex tidak dapat dijalankan: {exc}") from exc

    output = (result.stdout or "").strip()
    if result.returncode != 0:
        detail = (result.stderr or output or "Codex mengembalikan kegagalan.").strip()
        raise CodexIntegrationError(detail[-600:])
    if not output:
        raise CodexIntegrationError("Codex tidak mengembalikan notulen.")
    return output
