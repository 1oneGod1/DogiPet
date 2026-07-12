"""Persistent life-simulation data for Dogi profiles and their world.

This module intentionally has no Tkinter dependency so personality,
relationships, training, inventory, moods, seasons, and album metadata can be
tested without opening desktop windows.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any


PERSONALITIES = ("ceria", "aktif", "manja", "pemalu", "usil")
TRICKS = ("duduk", "tiarap", "putar", "lompat", "salaman", "pura_tidur")
TOYS = ("bola", "frisbee", "tali", "boneka")
HOMES = ("kasur", "rumah")
ACCESSORIES = ("none", "bandana", "star", "crown", "collar", "glasses", "party_hat")


def _default_profile(index: int, theme: str = "Shiba") -> dict[str, Any]:
    return {
        "id": f"dogi-{index}",
        "name": "Dogi" if index == 1 else f"Dogi {index}",
        "theme": theme,
        "personality": PERSONALITIES[(index - 1) % len(PERSONALITIES)],
        "training": {trick: 0 for trick in TRICKS},
        "inventory": ["none", "bandana"],
        "equipped": "none",
    }


def relationship_key(first_id: str, second_id: str) -> str:
    return "|".join(sorted((str(first_id), str(second_id))))


def mood_for(stats: dict[str, float], hour: int, state: str = "idle") -> str:
    """Return a compact visible mood without using AI or private data."""
    hungry = float(stats.get("kenyang", 100)) < 30
    tired = float(stats.get("energi", 100)) < 30
    lonely = float(stats.get("senang", 100)) < 30
    if hungry:
        return "LAPAR"
    if tired or hour >= 23 or hour < 6:
        return "MENGANTUK"
    if lonely:
        return "BUTUH TEMAN"
    if state in {"friend_play", "friend_chase", "friend_tussle", "toy_play"}:
        return "GEMBIRA"
    if state in {"think", "type", "meeting_watch"}:
        return "FOKUS"
    if state in {"dizzy", "hold"}:
        return "KAGET"
    return "SANTAI"


def seasonal_event(moment: datetime | None = None) -> dict[str, str]:
    """Small offline seasonal themes; no network, location, or tracking."""
    moment = moment or datetime.now()
    month, day = moment.month, moment.day
    if (month == 12 and day >= 20) or (month == 1 and day <= 5):
        return {"id": "salju", "label": "FESTIVAL SALJU", "accent": "#dcecff"}
    if month == 10 and day >= 25:
        return {"id": "kostum", "label": "MALAM KOSTUM", "accent": "#f29b45"}
    if month in (3, 4):
        return {"id": "bunga", "label": "MUSIM BUNGA", "accent": "#f2a8c2"}
    if month in (6, 7, 8):
        return {"id": "piknik", "label": "PIKNIK MUSIM PANAS", "accent": "#ffd34e"}
    return {"id": "harian", "label": "HARI BIASA YANG NYAMAN", "accent": "#ffd34e"}


def media_reaction_for(title: str) -> str | None:
    """Infer media context from a visible window title; audio is never read."""
    value = (title or "").casefold()
    music = ("spotify", "youtube music", "soundcloud", "musicbee", "foobar2000")
    calm = ("lofi", "lo-fi", "ambient", "sleep music", "relaxing music")
    if any(word in value for word in calm):
        return "calm"
    if any(word in value for word in music):
        return "dance"
    return None


class PetLifeStore:
    """JSON-backed profiles with conservative validation and migration."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, Any] = {
            "next_id": 2,
            "profiles": [_default_profile(1)],
            "relationships": {},
            "album": [],
            "home": {},
            "preferences": {
                "media_reaction": True,
                "sound_reaction": False,
                "mood_bubbles": True,
                "seasonal_events": True,
            },
        }
        self.load()

    @property
    def profiles(self) -> list[dict[str, Any]]:
        return self.data["profiles"]

    def load(self) -> None:
        try:
            incoming = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(incoming, dict):
            return
        profiles = incoming.get("profiles")
        if isinstance(profiles, list) and profiles:
            cleaned = []
            for index, raw in enumerate(profiles[:4], start=1):
                if not isinstance(raw, dict):
                    continue
                profile = _default_profile(index, str(raw.get("theme") or "Shiba"))
                profile["id"] = str(raw.get("id") or profile["id"])[:40]
                profile["name"] = str(raw.get("name") or profile["name"])[:24]
                personality = str(raw.get("personality") or "ceria")
                profile["personality"] = personality if personality in PERSONALITIES else "ceria"
                training = raw.get("training") or {}
                profile["training"] = {
                    trick: max(0, min(100, int(training.get(trick, 0))))
                    for trick in TRICKS
                }
                inventory = raw.get("inventory") or ["none"]
                profile["inventory"] = [
                    item for item in ACCESSORIES if item in inventory
                ] or ["none"]
                equipped = str(raw.get("equipped") or "none")
                profile["equipped"] = (
                    equipped if equipped in profile["inventory"] else "none"
                )
                cleaned.append(profile)
            if cleaned:
                self.data["profiles"] = cleaned
        relationships = incoming.get("relationships")
        if isinstance(relationships, dict):
            self.data["relationships"] = {
                str(key): max(0, min(100, int(value)))
                for key, value in relationships.items()
                if isinstance(value, (int, float))
            }
        album = incoming.get("album")
        if isinstance(album, list):
            self.data["album"] = [item for item in album[-200:] if isinstance(item, dict)]
        home = incoming.get("home")
        if isinstance(home, dict):
            self.data["home"] = deepcopy(home)
        preferences = incoming.get("preferences")
        if isinstance(preferences, dict):
            self.data["preferences"].update({
                key: bool(preferences[key])
                for key in self.data["preferences"]
                if key in preferences
            })
        self.data["next_id"] = max(
            int(incoming.get("next_id") or 1), len(self.profiles) + 1
        )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)

    def profile(self, profile_id: str) -> dict[str, Any]:
        for profile in self.profiles:
            if profile["id"] == profile_id:
                return profile
        return self.profiles[0]

    def add_profile(self, theme: str) -> dict[str, Any]:
        if len(self.profiles) >= 4:
            return self.profiles[-1]
        index = int(self.data.get("next_id") or len(self.profiles) + 1)
        self.data["next_id"] = index + 1
        profile = _default_profile(index, theme)
        self.profiles.append(profile)
        for other in self.profiles[:-1]:
            self.data["relationships"][relationship_key(profile["id"], other["id"])] = 20
        self.save()
        return profile

    def remove_profile(self, profile_id: str) -> None:
        if len(self.profiles) <= 1:
            return
        self.data["profiles"] = [p for p in self.profiles if p["id"] != profile_id]
        self.data["relationships"] = {
            key: value for key, value in self.data["relationships"].items()
            if profile_id not in key.split("|")
        }
        self.save()

    def set_personality(self, profile_id: str, personality: str) -> None:
        if personality not in PERSONALITIES:
            raise ValueError("Kepribadian Dogi tidak dikenal.")
        self.profile(profile_id)["personality"] = personality
        self.save()

    def relationship(self, first_id: str, second_id: str) -> int:
        if first_id == second_id:
            return 100
        return int(self.data["relationships"].get(
            relationship_key(first_id, second_id), 20
        ))

    def adjust_relationship(self, first_id: str, second_id: str, amount: int) -> int:
        key = relationship_key(first_id, second_id)
        value = max(0, min(100, self.relationship(first_id, second_id) + int(amount)))
        self.data["relationships"][key] = value
        self.save()
        return value

    def train(self, profile_id: str, trick: str, amount: int = 8) -> int:
        if trick not in TRICKS:
            raise ValueError("Trik Dogi tidak dikenal.")
        profile = self.profile(profile_id)
        value = max(0, min(100, int(profile["training"].get(trick, 0)) + amount))
        profile["training"][trick] = value
        if value >= 50:
            reward = {
                "duduk": "collar",
                "putar": "glasses",
                "lompat": "party_hat",
            }.get(trick)
            if reward and reward not in profile["inventory"]:
                profile["inventory"].append(reward)
        self.save()
        return value

    def equip(self, profile_id: str, accessory: str) -> None:
        profile = self.profile(profile_id)
        if accessory not in profile["inventory"]:
            raise ValueError("Aksesori belum terbuka.")
        profile["equipped"] = accessory
        self.save()

    def add_inventory(self, profile_id: str, accessory: str) -> None:
        if accessory not in ACCESSORIES:
            raise ValueError("Aksesori tidak dikenal.")
        profile = self.profile(profile_id)
        if accessory not in profile["inventory"]:
            profile["inventory"].append(accessory)
            self.save()

    def add_album_entry(
        self, event: str, profile_id: str, image_path: str, created_at: str | None = None
    ) -> dict[str, str]:
        entry = {
            "event": str(event)[:60],
            "profile_id": str(profile_id),
            "image_path": str(image_path),
            "created_at": created_at or datetime.now().isoformat(timespec="seconds"),
        }
        self.data["album"].append(entry)
        self.data["album"] = self.data["album"][-200:]
        self.save()
        return entry

    def set_home(self, kind: str, x: int, y: int) -> None:
        if kind not in HOMES:
            raise ValueError("Jenis rumah Dogi tidak dikenal.")
        self.data["home"] = {"kind": kind, "x": int(x), "y": int(y)}
        self.save()

    def preference(self, key: str) -> bool:
        return bool(self.data["preferences"].get(key, False))

    def toggle_preference(self, key: str) -> bool:
        if key not in self.data["preferences"]:
            raise ValueError("Preferensi Dogi tidak dikenal.")
        value = not bool(self.data["preferences"][key])
        self.data["preferences"][key] = value
        self.save()
        return value
