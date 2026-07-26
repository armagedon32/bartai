from typing import Any


class Tool:
    name: str = ""
    description: str = ""
    parameters: dict = {}

    def execute(self, **kwargs) -> str:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return f"Error executing {name}: {e}"
