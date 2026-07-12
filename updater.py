"""Pembaruan DogiPet melalui GitHub Releases.

Modul ini hanya memakai Python standard library agar tetap ringan. Pekerjaan
jaringan dilakukan di thread terpisah dan hasilnya dikirim ke UI melalui
queue, sehingga loop animasi Tkinter tidak macet.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import pathlib
import queue
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request

from build_info import BUILD_ID
from version import VERSION


REPOSITORY = "1oneGod1/DogiPet"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"
RELEASE_PAGE = f"https://github.com/{REPOSITORY}/releases"
USER_AGENT = f"DogiPet/{VERSION}"
INSTALLER_ASSET = "DogiPet-Setup.exe"
CHECKSUM_ASSET = f"{INSTALLER_ASSET}.sha256"
MANIFEST_ASSET = "build-info.json"
MAX_DOWNLOAD_BYTES = 250 * 1024 * 1024


class UpdateError(RuntimeError):
    """Kesalahan yang aman ditampilkan kepada pengguna."""


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    build_id: str
    channel: str
    installer_url: str
    checksum_url: str
    release_url: str
    notes: str = ""


def _version_tuple(value: str) -> tuple[int, ...]:
    """Ubah versi sederhana seperti v1.2.3 menjadi tuple yang bisa dibandingkan."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", value.strip())
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(candidate: str, current: str) -> bool:
    comparison = compare_versions(candidate, current)
    return comparison is not None and comparison > 0


def compare_versions(candidate: str, current: str) -> int | None:
    """Bandingkan versi; hasil -1/0/1, atau None bila format tidak valid."""
    candidate_parts = _version_tuple(candidate)
    current_parts = _version_tuple(current)
    if not candidate_parts or not current_parts:
        return None
    width = max(len(candidate_parts), len(current_parts))
    candidate_parts += (0,) * (width - len(candidate_parts))
    current_parts += (0,) * (width - len(current_parts))
    return (candidate_parts > current_parts) - (candidate_parts < current_parts)


def _request_json(url: str, timeout: int = 15) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("Belum ada rilis pembaruan di GitHub.") from exc
        raise UpdateError(f"GitHub mengembalikan status HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UpdateError("Tidak dapat menghubungi layanan pembaruan GitHub.") from exc


def _asset_map(release: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for asset in release.get("assets", []):
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if isinstance(name, str) and isinstance(url, str):
            result[name] = url
    return result


def get_update_info(
    channel: str = "stable",
    current_version: str = VERSION,
    current_build: str = BUILD_ID,
) -> UpdateInfo | None:
    """Ambil pembaruan terbaru untuk kanal stable atau continuous."""
    channel = "continuous" if channel == "continuous" else "stable"
    endpoint = (
        f"{API_ROOT}/releases/tags/continuous"
        if channel == "continuous"
        else f"{API_ROOT}/releases/latest"
    )
    release = _request_json(endpoint)
    assets = _asset_map(release)
    missing = [
        name for name in (INSTALLER_ASSET, CHECKSUM_ASSET, MANIFEST_ASSET)
        if name not in assets
    ]
    if missing:
        raise UpdateError("Rilis GitHub belum memiliki paket installer yang lengkap.")

    manifest = _request_json(assets[MANIFEST_ASSET])
    version = str(manifest.get("version") or release.get("tag_name") or "").lstrip("v")
    build_id = str(manifest.get("build_id") or "")
    if channel == "continuous":
        # Continuous membedakan build berdasarkan commit, tetapi tidak boleh
        # menawarkan manifest dengan versi semantik lebih rendah. Sebelumnya
        # build 0.5.4 dianggap update untuk instalasi lokal 0.6.1 hanya karena
        # SHA-nya berbeda, sehingga tombol Yes justru melakukan downgrade.
        version_order = compare_versions(version, current_version)
        has_update = bool(
            version_order is not None
            and version_order >= 0
            and build_id
            and build_id not in {current_build, "source"}
        )
    else:
        has_update = is_newer_version(version, current_version)
    if not has_update:
        return None

    return UpdateInfo(
        version=version,
        build_id=build_id,
        channel=channel,
        installer_url=assets[INSTALLER_ASSET],
        checksum_url=assets[CHECKSUM_ASSET],
        release_url=str(release.get("html_url") or RELEASE_PAGE),
        notes=str(release.get("body") or ""),
    )


def _download(url: str, destination: pathlib.Path, limit: int = MAX_DOWNLOAD_BYTES) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content_length = int(response.headers.get("Content-Length", "0") or 0)
            if content_length > limit:
                raise UpdateError("Ukuran paket pembaruan melebihi batas aman.")
            total = 0
            with destination.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit:
                        raise UpdateError("Ukuran paket pembaruan melebihi batas aman.")
                    handle.write(chunk)
    except (urllib.error.URLError, TimeoutError, OSError, UpdateError) as exc:
        destination.unlink(missing_ok=True)
        if isinstance(exc, UpdateError):
            raise
        raise UpdateError("Paket pembaruan gagal diunduh.") from exc


def download_installer(info: UpdateInfo) -> pathlib.Path:
    update_dir = pathlib.Path.home() / ".dogi" / "updates"
    update_dir.mkdir(parents=True, exist_ok=True)
    safe_build = re.sub(r"[^a-zA-Z0-9._-]", "-", info.build_id or info.version)
    installer = update_dir / f"DogiPet-Setup-{safe_build}.exe"
    checksum_file = update_dir / f"{installer.name}.sha256"
    partial = installer.with_suffix(".download")

    _download(info.installer_url, partial)
    _download(info.checksum_url, checksum_file, limit=4096)
    expected = checksum_file.read_text(encoding="utf-8").strip().split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        partial.unlink(missing_ok=True)
        raise UpdateError("Checksum rilis tidak valid.")

    digest = hashlib.sha256()
    with partial.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest().lower() != expected:
        partial.unlink(missing_ok=True)
        raise UpdateError("Verifikasi paket pembaruan gagal.")

    partial.replace(installer)
    return installer


def launch_installer(installer: pathlib.Path) -> None:
    if sys.platform != "win32":
        raise UpdateError("Pemasangan otomatis saat ini hanya tersedia di Windows.")
    subprocess.Popen(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
        ],
        close_fds=True,
    )


class UpdateManager:
    """Jembatan thread updater dengan loop utama Tkinter."""

    def __init__(self) -> None:
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False

    def check_async(self, channel: str, manual: bool = False) -> bool:
        if self.busy:
            return False
        self.busy = True

        def worker() -> None:
            try:
                info = get_update_info(channel=channel)
                event = ("available" if info else "current", info or manual)
            except Exception as exc:  # thread boundary: kirim pesan ke UI
                event = ("error", (exc, manual))
            self.busy = False
            self.events.put(event)

        threading.Thread(target=worker, daemon=True, name="dogipet-update-check").start()
        return True

    def download_async(self, info: UpdateInfo) -> bool:
        if self.busy:
            return False
        self.busy = True

        def worker() -> None:
            try:
                event = ("downloaded", download_installer(info))
            except Exception as exc:
                event = ("download_error", exc)
            self.busy = False
            self.events.put(event)

        threading.Thread(target=worker, daemon=True, name="dogipet-update-download").start()
        return True

    def poll(self) -> list[tuple[str, object]]:
        result: list[tuple[str, object]] = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except queue.Empty:
                return result
