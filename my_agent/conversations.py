import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


class ConversationManager:
    def __init__(self, conv_dir: str):
        self.conv_dir = Path(conv_dir)
        self.conv_dir.mkdir(parents=True, exist_ok=True)
        self.current = "default"
        self._conversations: dict[str, list[dict[str, Any]]] = {}
        self._metadatas: dict[str, dict] = {}
        self._load_all()

    def _conv_path(self, name: str) -> Path:
        return self.conv_dir / f"{name}.json"

    def _meta_path(self, name: str) -> Path:
        return self.conv_dir / f"{name}.meta.json"

    def _load_all(self):
        for f in self.conv_dir.glob("*.json"):
            if f.name.endswith(".meta.json"):
                continue
            name = f.stem
            try:
                self._conversations[name] = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, FileNotFoundError):
                self._conversations[name] = []

            meta = self._meta_path(name)
            if meta.exists():
                try:
                    self._metadatas[name] = json.loads(meta.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, FileNotFoundError):
                    self._metadatas[name] = {}
            else:
                self._metadatas[name] = {}

        if "default" not in self._conversations:
            self._conversations["default"] = []
            self._metadatas["default"] = {"created": datetime.now().isoformat()}
            self._save("default")

    def _save(self, name: str | None = None):
        name = name or self.current
        if name in self._conversations:
            msgs = self._conversations[name]
            self._conv_path(name).write_text(
                json.dumps(msgs, indent=2, default=str), encoding="utf-8"
            )
        if name in self._metadatas:
            self._meta_path(name).write_text(
                json.dumps(self._metadatas[name], indent=2), encoding="utf-8"
            )

    def list_all(self) -> list[dict]:
        result = []
        for name in self._conversations:
            meta = self._metadatas.get(name, {})
            msg_count = len(self._conversations.get(name, []))
            created = meta.get("created", "unknown")
            model = meta.get("model", "")
            info = f" | model: {model}" if model else ""
            result.append({
                "name": name,
                "messages": msg_count,
                "created": created,
                "label": f"{name} ({msg_count} msgs, created {created[:10]}){info}",
                "current": name == self.current,
            })
        result.sort(key=lambda x: x["name"])
        return result

    def switch(self, name: str, create: bool = True) -> str:
        if name not in self._conversations:
            if not create:
                return f"Conversation '{name}' not found."
            self._conversations[name] = []
            self._metadatas[name] = {"created": datetime.now().isoformat()}
            self._save(name)
        self.current = name
        return f"Switched to conversation '{name}'"

    def delete(self, name: str) -> str:
        if name == "default":
            return "Cannot delete the default conversation."
        if name not in self._conversations:
            return f"Conversation '{name}' not found."
        del self._conversations[name]
        del self._metadatas[name]
        self._conv_path(name).unlink(missing_ok=True)
        self._meta_path(name).unlink(missing_ok=True)
        if self.current == name:
            self.current = "default"
            return f"Deleted '{name}'. Switched to 'default'."
        return f"Deleted '{name}'."

    def rename(self, old: str, new: str) -> str:
        if old not in self._conversations:
            return f"Conversation '{old}' not found."
        if new in self._conversations:
            return f"Conversation '{new}' already exists."
        self._conversations[new] = self._conversations.pop(old)
        self._metadatas[new] = self._metadatas.pop(old, {})
        self._save(new)
        self._conv_path(old).unlink(missing_ok=True)
        self._meta_path(old).unlink(missing_ok=True)
        if self.current == old:
            self.current = new
        return f"Renamed '{old}' to '{new}'."

    def add_message(self, msg: dict, name: str | None = None):
        name = name or self.current
        if name not in self._conversations:
            self._conversations[name] = []
        self._conversations[name].append(msg)
        self._save(name)

    def get_history(self, name: str | None = None, limit: int = 100) -> list[dict]:
        name = name or self.current
        msgs = self._conversations.get(name, [])
        return msgs[-limit:]

    def clear(self, name: str | None = None):
        name = name or self.current
        self._conversations[name] = []
        self._save(name)

    def export_markdown(self, name: str | None = None) -> str:
        name = name or self.current
        msgs = self._conversations.get(name, [])
        lines = [f"# Conversation: {name}", ""]
        for m in msgs:
            role = m["role"].upper()
            content = m.get("content", "")
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    fn = tc["function"]
                    lines.append(f"## {role} (tool: {fn['name']})")
                    lines.append("```json")
                    lines.append(fn["arguments"])
                    lines.append("```")
                    lines.append("")
            elif m["role"] == "tool":
                lines.append(f"## TOOL RESULT: {m.get('content', '')[:100]}")
                lines.append("")
            else:
                lines.append(f"## {role}")
                lines.append("")
                lines.append(content)
                lines.append("")
        return "\n".join(lines)

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        query_lower = query.lower()
        results = []
        for name, msgs in self._conversations.items():
            for i, m in enumerate(msgs):
                content = (m.get("content") or "").lower()
                if query_lower in content:
                    results.append({
                        "conversation": name,
                        "index": i,
                        "role": m["role"],
                        "snippet": (m.get("content") or "")[:300],
                    })
        results.sort(key=lambda r: r["conversation"])
        return results[:max_results]
