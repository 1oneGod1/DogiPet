"""Plugin deklaratif DogiPet: JSON tervalidasi, tanpa eksekusi kode."""

from __future__ import annotations
import json
from pathlib import Path

ALLOWED_EVENTS = {"morning", "evening", "focus_done", "task_done", "fed"}
ALLOWED_STATES = {"happy", "curious", "tail_wag", "beg", "jump", "idle"}


class PluginManager:
    def __init__(self, folder): self.folder = Path(folder); self.plugins = []

    def reload(self):
        self.folder.mkdir(parents=True, exist_ok=True); loaded=[]
        for path in sorted(self.folder.glob("*.json")):
            try: data=json.loads(path.read_text(encoding="utf-8"))
            except Exception: continue
            if not isinstance(data,dict) or not str(data.get("name") or "").strip(): continue
            triggers=[]
            for raw in data.get("triggers",[]):
                if not isinstance(raw,dict) or raw.get("event") not in ALLOWED_EVENTS: continue
                message=str(raw.get("message") or "").strip()[:120]
                if not message: continue
                state=raw.get("state") if raw.get("state") in ALLOWED_STATES else "happy"
                triggers.append({"event":raw["event"],"message":message,"state":state})
            loaded.append({"name":str(data["name"])[:80],"path":path,"triggers":triggers})
        self.plugins=loaded; return loaded

    def triggers_for(self,event):
        return [trigger for plugin in self.plugins for trigger in plugin["triggers"] if trigger["event"]==event]

    def create_template(self):
        self.folder.mkdir(parents=True,exist_ok=True); path=self.folder/"contoh-plugin.json"
        if not path.exists():
            path.write_text(json.dumps({"name":"Sapaan Dogi","version":1,"triggers":[{"event":"morning","message":"Semangat hari ini!","state":"tail_wag"},{"event":"task_done","message":"Hebat! Satu tugas selesai.","state":"happy"}]},ensure_ascii=False,indent=2),encoding="utf-8")
        self.reload(); return path
