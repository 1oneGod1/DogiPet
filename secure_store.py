"""Penyimpanan kredensial DogiPet yang dienkripsi untuk pengguna Windows.

File konfigurasi biasa sengaja tidak memuat API key atau token OAuth. Seluruh
nilai sensitif disimpan sebagai satu blob JSON yang dilindungi Windows DPAPI,
sehingga hanya akun Windows yang sama yang dapat membukanya.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import threading
from typing import Any, Callable


class SecureStoreError(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _input_blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(
        len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    )
    return blob, buffer


def _windows_protect(data: bytes) -> bytes:
    if not sys.platform.startswith("win"):
        raise SecureStoreError("DPAPI hanya tersedia di Windows.")
    source, source_buffer = _input_blob(data)
    destination = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    ok = crypt32.CryptProtectData(
        ctypes.byref(source),
        "DogiPet credentials",
        None,
        None,
        None,
        0x01,  # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(destination),
    )
    if not ok:
        raise SecureStoreError(str(ctypes.WinError()))
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


def _windows_unprotect(data: bytes) -> bytes:
    if not sys.platform.startswith("win"):
        raise SecureStoreError("DPAPI hanya tersedia di Windows.")
    source, source_buffer = _input_blob(data)
    destination = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0x01,
        ctypes.byref(destination),
    )
    if not ok:
        raise SecureStoreError(
            "Kredensial tidak dapat dibuka oleh akun Windows ini."
        )
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


class SecureStore:
    """Dictionary kecil terenkripsi dengan penulisan atomik."""

    def __init__(
        self,
        path: str | Path,
        protect: Callable[[bytes], bytes] | None = None,
        unprotect: Callable[[bytes], bytes] | None = None,
    ):
        self.path = Path(path)
        self._protect = protect or _windows_protect
        self._unprotect = unprotect or _windows_unprotect
        self._lock = threading.RLock()

    @property
    def available(self) -> bool:
        return sys.platform.startswith("win") or (
            self._protect is not _windows_protect
            and self._unprotect is not _windows_unprotect
        )

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {}
            try:
                raw = self._unprotect(self.path.read_bytes())
                value = json.loads(raw.decode("utf-8"))
            except SecureStoreError:
                raise
            except Exception as exc:
                raise SecureStoreError("Penyimpanan kredensial rusak.") from exc
            if not isinstance(value, dict):
                raise SecureStoreError("Format penyimpanan kredensial tidak valid.")
            return value

    def save(self, values: dict[str, Any]) -> None:
        with self._lock:
            if not self.available:
                raise SecureStoreError("Penyimpanan aman hanya tersedia di Windows.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            plain = json.dumps(values, ensure_ascii=False).encode("utf-8")
            encrypted = self._protect(plain)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_bytes(encrypted)
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            os.replace(temporary, self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            values = self.load()
            values[key] = value
            self.save(values)

    def delete(self, key: str) -> None:
        with self._lock:
            values = self.load()
            if key in values:
                del values[key]
                self.save(values)
