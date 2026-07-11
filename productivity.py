"""Tugas, memori, pencarian, progression, dan backup DogiPet."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


@dataclass
class Task:
    id: str
    title: str
    details: str
    status: str
    priority: str
    due_at: str
    source: str
    created_at: str
    updated_at: str

    @property
    def done(self) -> bool:
        return self.status == "done"

    def display(self) -> str:
        box = "✓" if self.done else "□"
        due = ""
        if self.due_at:
            try:
                due = " / " + datetime.fromisoformat(self.due_at).astimezone().strftime("%d %b %H:%M")
            except ValueError:
                due = " / " + self.due_at[:16]
        return f"{box} [{self.priority.upper()}] {self.title}{due}"


class TaskStore:
    VALID_STATUS = {"todo", "doing", "done"}
    VALID_PRIORITY = {"low", "normal", "high"}

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def all(self) -> list[Task]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8")).get("tasks", [])
            tasks = [Task(**item) for item in raw if isinstance(item, dict)]
        except Exception as exc:
            raise RuntimeError("File tugas Dogi tidak dapat dibaca.") from exc
        return sorted(tasks, key=lambda item: (item.done, item.due_at or "9999", item.created_at))

    def _write(self, tasks: list[Task]) -> None:
        _atomic_json(self.path, {"version": 1, "tasks": [asdict(item) for item in tasks]})

    def get(self, task_id: str) -> Task | None:
        return next((item for item in self.all() if item.id == task_id), None)

    def create(self, title: str, details: str = "", *, priority="normal", due_at="", source="manual") -> Task:
        title = str(title or "").strip()
        if not title:
            raise ValueError("Judul tugas masih kosong.")
        priority = priority if priority in self.VALID_PRIORITY else "normal"
        stamp = _now_iso()
        task = Task(uuid.uuid4().hex, title[:120], str(details or "").strip(), "todo", priority, str(due_at or ""), str(source or "manual")[:80], stamp, stamp)
        tasks = self.all(); tasks.append(task); self._write(tasks)
        return task

    def update(self, task_id: str, **changes) -> Task:
        tasks = self.all()
        for index, item in enumerate(tasks):
            if item.id != task_id:
                continue
            data = asdict(item)
            for key in ("title", "details", "due_at", "source"):
                if key in changes:
                    data[key] = str(changes[key] or "").strip()
            if changes.get("status") in self.VALID_STATUS:
                data["status"] = changes["status"]
            if changes.get("priority") in self.VALID_PRIORITY:
                data["priority"] = changes["priority"]
            data["title"] = data["title"][:120] or "Tanpa judul"
            data["updated_at"] = _now_iso()
            changed = Task(**data); tasks[index] = changed; self._write(tasks)
            return changed
        raise ValueError("Tugas tidak ditemukan.")

    def toggle_done(self, task_id: str) -> tuple[Task, bool]:
        item = self.get(task_id)
        if not item:
            raise ValueError("Tugas tidak ditemukan.")
        newly_done = not item.done
        return self.update(task_id, status="done" if newly_done else "todo"), newly_done

    def delete(self, task_id: str) -> bool:
        tasks = self.all(); kept = [item for item in tasks if item.id != task_id]
        if len(kept) == len(tasks): return False
        self._write(kept); return True


@dataclass
class Memory:
    id: str
    label: str
    value: str
    enabled: bool
    updated_at: str


class MemoryStore:
    def __init__(self, path: str | Path): self.path = Path(path)

    def all(self) -> list[Memory]:
        if not self.path.exists(): return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8")).get("memories", [])
            return [Memory(**item) for item in raw if isinstance(item, dict)]
        except Exception as exc:
            raise RuntimeError("File memori Dogi tidak dapat dibaca.") from exc

    def _write(self, items): _atomic_json(self.path, {"version": 1, "memories": [asdict(item) for item in items]})

    def create(self, label: str, value: str) -> Memory:
        label, value = str(label or "").strip(), str(value or "").strip()
        if not label or not value: raise ValueError("Nama dan isi memori wajib diisi.")
        item = Memory(uuid.uuid4().hex, label[:80], value[:1000], True, _now_iso())
        items = self.all(); items.append(item); self._write(items); return item

    def delete(self, memory_id: str) -> bool:
        items = self.all(); kept = [item for item in items if item.id != memory_id]
        if len(kept) == len(items): return False
        self._write(kept); return True

    def toggle(self, memory_id: str) -> Memory:
        items = self.all()
        for index, item in enumerate(items):
            if item.id == memory_id:
                changed = Memory(item.id, item.label, item.value, not item.enabled, _now_iso())
                items[index] = changed; self._write(items); return changed
        raise ValueError("Memori tidak ditemukan.")


@dataclass(frozen=True)
class SearchResult:
    kind: str
    title: str
    preview: str

    def display(self): return f"[{self.kind.upper()}] {self.title} — {self.preview}"


def global_search(query, *, notes, tasks, memories, transcript_dir, calendar_events, limit=50):
    words = [word for word in re.findall(r"\w+", str(query or "").lower()) if len(word) > 1]
    if not words: return []
    results = []
    def add(kind, title, text):
        hay = f"{title}\n{text}".lower()
        if all(word in hay for word in words):
            clean = " ".join(str(text or "").split())[:160]
            results.append(SearchResult(kind, str(title)[:100], clean))
    for item in notes: add("catatan", item.title, item.body)
    for item in tasks: add("tugas", item.title, f"{item.details} {item.status} {item.due_at}")
    for item in memories: add("memori", item.label, item.value)
    for event in calendar_events: add("agenda", event.title, event.display())
    folder = Path(transcript_dir)
    if folder.is_dir():
        for path in sorted(folder.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            try: add("transkrip", path.name, path.read_text(encoding="utf-8")[:20000])
            except (OSError, UnicodeError): pass
    return results[:limit]


ACCESSORY_LEVELS = {"none": 1, "bandana": 2, "star": 3, "crown": 5}


def progression_level(xp: int) -> int: return max(1, int(xp) // 100 + 1)
def accessory_unlocked(name: str, xp: int) -> bool: return progression_level(xp) >= ACCESSORY_LEVELS.get(name, 999)


def export_task_ics(task: Task, path: str | Path) -> Path:
    if not task.due_at:
        raise ValueError("Tugas belum memiliki deadline.")
    try:
        start = datetime.fromisoformat(task.due_at).astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError("Deadline tugas tidak valid.") from exc
    from datetime import timedelta
    end = start + timedelta(hours=1)
    def esc(value):
        return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
    content = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DogiPet//Task//ID",
        "BEGIN:VEVENT", f"UID:{task.id}@dogipet.local",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{esc(task.title)}", f"DESCRIPTION:{esc(task.details)}",
        "END:VEVENT", "END:VCALENDAR", "",
    ])
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="")
    return target


BACKUP_MAGIC = b"DOGIBAK1"


def export_encrypted_backup(path: str | Path, payload: dict, password: str) -> Path:
    if len(str(password or "")) < 8: raise ValueError("Password backup minimal 8 karakter.")
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc: raise RuntimeError("Komponen enkripsi backup belum tersedia.") from exc
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480_000).derive(password.encode("utf-8"))
    plain = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    encrypted = AESGCM(key).encrypt(nonce, plain, BACKUP_MAGIC)
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(BACKUP_MAGIC + salt + nonce + encrypted)
    return target


def import_encrypted_backup(path: str | Path, password: str) -> dict:
    raw = Path(path).read_bytes()
    if not raw.startswith(BACKUP_MAGIC) or len(raw) < 40: raise ValueError("File backup DogiPet tidak valid.")
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc: raise RuntimeError("Komponen enkripsi backup belum tersedia.") from exc
    salt, nonce, encrypted = raw[8:24], raw[24:36], raw[36:]
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480_000).derive(str(password or "").encode("utf-8"))
    try: plain = AESGCM(key).decrypt(nonce, encrypted, BACKUP_MAGIC)
    except Exception as exc: raise ValueError("Password salah atau backup rusak.") from exc
    payload = json.loads(plain.decode("utf-8"))
    if not isinstance(payload, dict): raise ValueError("Isi backup DogiPet tidak valid.")
    return payload
