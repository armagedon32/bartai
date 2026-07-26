from my_agent.tools.registry import Tool


class MemorySearchTool(Tool):
    name = "search_memory"
    description = "Search past conversations and stored knowledge for relevant information. Use this when the user asks about something you discussed before or when you need context from earlier interactions."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant past information",
            },
        },
        "required": ["query"],
    }

    def __init__(self, memory_index=None):
        super().__init__()
        self.memory_index = memory_index

    def execute(self, query: str) -> str:
        if not self.memory_index:
            return "Memory search is not available."
        results = self.memory_index.search(query, top_k=5)
        if not results:
            return "No relevant memories found."
        output = [f"Found {len(results)} relevant memory(s):"]
        for i, r in enumerate(results, 1):
            text = r["text"]
            meta = r.get("metadata", {})
            source = meta.get("conversation", "unknown")
            date = meta.get("date", "")[:10]
            tag = f" (from: {source}, {date})" if date else f" (from: {source})"
            output.append(f"\n{i}.{tag}\n   {text[:200]}")
        return "\n".join(output)
