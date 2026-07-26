import json
from typing import Any


class Memory:
    def __init__(self, filepath: str, max_history: int = 50):
        self.filepath = filepath
        self.max_history = max_history
        self.messages: list[dict[str, Any]] = []
        self._load()

    def _load(self):
        try:
            with open(self.filepath) as f:
                data = json.load(f)
                self.messages = data.get("messages", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.messages = []

    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump({"messages": self.messages[-self.max_history:]}, f, indent=2)

    def add(self, role: str, content: str, tool_calls: list | None = None):
        entry = {"role": role, "content": content}
        if tool_calls:
            entry["tool_calls"] = tool_calls
        self.messages.append(entry)
        self._save()

    def add_tool_result(self, tool_call_id: str, name: str, result: str):
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": str(result),
            }
        )

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.messages)

    def clear(self):
        self.messages = []
        self._save()
