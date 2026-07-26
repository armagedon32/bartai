import json
from datetime import datetime
from my_agent.config import Config
from my_agent.llm import LLMClient
from my_agent.conversations import ConversationManager
from my_agent.rag import MemoryIndex
from my_agent.tools import ToolRegistry, register_all
from my_agent.scheduler import TaskScheduler


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config)
        self.conversations = ConversationManager(str(config.conv_dir))
        self.memory_index = MemoryIndex(str(config.data_dir), embed_fn=self.llm.embed)
        self.tools = ToolRegistry()
        register_all(self.tools, self.memory_index)
        self.scheduler = TaskScheduler(str(config.tasks_file), self)

    def _build_messages(self):
        history = self.conversations.get_history()
        # Summarize old messages if conversation is too long
        if len(history) > 20:
            keep = history[-10:]
            to_summarize = history[:-10]
            summary = self._summarize_conversation(to_summarize)
            messages = [{"role": "system", "content": self.config.system_prompt}]
            if summary:
                messages.append({"role": "system", "content": f"[Previous conversation summary]: {summary}"})
            messages.extend(keep)
            return messages
        messages = [{"role": "system", "content": self.config.system_prompt}]
        messages.extend(history)
        return messages

    def _summarize_conversation(self, history: list[dict]) -> str:
        if not history:
            return ""
        text = ""
        for m in history:
            role = m["role"]
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
            if isinstance(content, str) and content.strip():
                text += f"{role}: {content[:500]}\n"
        if not text.strip():
            return ""
        try:
            resp = self.llm.client.chat.completions.create(
                model=self.llm._model_for_provider(),
                messages=[
                    {"role": "system", "content": "Summarize the key points of this conversation concisely in 2-3 sentences. Focus on what was discussed and any conclusions reached."},
                    {"role": "user", "content": text[:4000]},
                ],
                max_tokens=300,
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            return ""

    def _make_content(self, text: str, images: list[str] | None = None, files: list[dict] | None = None):
        text_parts = [text] if text else []
        if files:
            text_parts.append("\n\n--- Attached files ---")
            for f in files:
                ext = f.get("name", "").split(".")[-1] if "." in f.get("name", "") else ""
                text_parts.append(f"\n\n📄 {f['name']} ({f.get('type', 'unknown')}):")
                text_parts.append(f"\n```{ext}\n{f['content']}\n```")
        combined_text = "\n".join(text_parts).strip()

        if not images:
            return combined_text
        content: list = []
        if combined_text:
            content.append({"type": "text", "text": combined_text})
        for img in images:
            content.append({"type": "image_url", "image_url": {"url": img}})
        if not content:
            content.append({"type": "text", "text": "Analyze the attached files."})
        return content

    async def chat_stream_async(self, user_input: str, images: list[str] | None = None, files: list[dict] | None = None):
        content = self._make_content(user_input, images, files)
        msg = {"role": "user", "content": content}
        if images:
            msg["images"] = images
        if files:
            msg["files"] = [{"name": f["name"], "type": f.get("type", "text/plain")} for f in files]
        self.conversations.add_message(msg)
        conv = self.conversations

        for turn in range(self.config.max_turns):
            messages = self._build_messages()
            stream = await self.llm.chat_stream_async(messages, tools=self.tools.list_schemas())

            content_text = ""
            tool_calls = {}

            async for chunk in stream:
                if not chunk.choices:
                    if hasattr(chunk, "usage") and chunk.usage:
                        yield {"type": "usage", "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        }}
                    continue

                delta = chunk.choices[0].delta
                if not delta:
                    continue

                if delta.content:
                    content_text += delta.content
                    yield {"type": "token", "content": delta.content}

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls:
                            tool_calls[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
                        if tc.id:
                            tool_calls[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            if tool_calls:
                calls = list(tool_calls.values())
                conv.add_message({
                    "role": "assistant",
                    "content": content_text or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]} for tc in calls
                    ],
                })
                yield {"type": "tool_calls", "tool_calls": calls}
                for tc in calls:
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    result = self.tools.execute(tc["function"]["name"], args)
                    conv.add_message({
                        "role": "tool", "tool_call_id": tc["id"], "content": str(result),
                    })
                    yield {"type": "tool_result", "name": tc["function"]["name"], "result": result}
                continue

            conv.add_message({"role": "assistant", "content": content_text})
            self.memory_index.add_text(
                f"User: {user_input}\nAssistant: {content_text[:500]}",
                {"conversation": conv.current, "date": datetime.now().isoformat()},
            )
            yield {"type": "done", "content": content_text}
            return

        yield {"type": "error", "content": "Max turns reached without completing the response."}

    def chat_stream(self, user_input: str):
        self.conversations.add_message({"role": "user", "content": user_input})
        conv = self.conversations

        for turn in range(self.config.max_turns):
            messages = [{"role": "system", "content": self.config.system_prompt}]
            messages.extend(conv.get_history())

            stream = self.llm.chat_stream(messages, tools=self.tools.list_schemas())

            content = ""
            tool_calls = {}

            for chunk in stream:
                if not chunk.choices:
                    if hasattr(chunk, "usage") and chunk.usage:
                        yield {"type": "usage", "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        }}
                    continue

                delta = chunk.choices[0].delta
                if not delta:
                    continue

                if delta.content:
                    content += delta.content
                    yield {"type": "token", "content": delta.content}

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls:
                            tool_calls[idx] = {
                                "id": "",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            tool_calls[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            if tool_calls:
                calls = list(tool_calls.values())
                conv.add_message({
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in calls
                    ],
                })

                yield {"type": "tool_calls", "tool_calls": calls}

                for tc in calls:
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    result = self.tools.execute(tc["function"]["name"], args)
                    conv.add_message({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(result),
                    })
                    yield {"type": "tool_result", "name": tc["function"]["name"], "result": result}
                continue

            conv.add_message({"role": "assistant", "content": content})
            self.memory_index.add_text(
                f"User: {user_input}\nAssistant: {content[:500]}",
                {"conversation": conv.current, "date": datetime.now().isoformat()},
            )
            yield {"type": "done", "content": content}
            return

        yield {"type": "error", "content": "Max turns reached without completing the response."}

    def run_task(self, prompt: str) -> str:
        messages = [{"role": "system", "content": self.config.system_prompt}, {"role": "user", "content": prompt}]
        for _ in range(self.config.max_turns):
            reply = self.llm.chat(messages, tools=self.tools.list_schemas())
            messages.append(reply)
            if reply.get("tool_calls"):
                for tc in reply["tool_calls"]:
                    args = json.loads(tc["function"]["arguments"])
                    result = self.tools.execute(tc["function"]["name"], args)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})
            else:
                return reply["content"]
        return "Max turns reached without final answer."

    def handle_command(self, cmd: str) -> str | None:
        parts = cmd.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if command == "/clear":
            self.conversations.clear()
            return "Current conversation cleared."

        if command == "/new":
            name = arg.strip() or f"conv_{len(self.conversations.list_all())}"
            self.conversations.switch(name)
            return f"Started new conversation '{name}'."

        if command == "/list":
            convs = self.conversations.list_all()
            if not convs:
                return "No conversations."
            lines = ["Conversations:"]
            for c in convs:
                marker = " *" if c["current"] else "  "
                lines.append(f"  {marker} {c['label']}")
            return "\n".join(lines)

        if command in ("/switch", "/open"):
            if not arg:
                return "Usage: /switch conversation_name"
            return self.conversations.switch(arg.strip())

        if command == "/rename":
            parts2 = arg.split(maxsplit=1)
            if len(parts2) < 2:
                return "Usage: /rename old_name new_name"
            return self.conversations.rename(parts2[0].strip(), parts2[1].strip())

        if command == "/delete":
            if not arg:
                return f"Usage: /delete conversation_name"
            return self.conversations.delete(arg.strip())

        if command == "/export":
            name = arg.strip() or None
            md = self.conversations.export_markdown(name)
            path = self.config.data_dir / f"export_{self.conversations.current}.md"
            path.write_text(md, encoding="utf-8")
            return f"Exported to {path}"

        if command == "/tasks":
            return self.scheduler.list_tasks()

        if command == "/task_add":
            try:
                name, interval, prompt_text = arg.split("|", 2)
                return self.scheduler.add_task(name.strip(), prompt_text.strip(), int(interval.strip()))
            except Exception:
                return "Usage: /task_add name | interval_hours | prompt"

        if command == "/task_rm":
            return self.scheduler.remove_task(arg.strip())

        if command == "/model":
            if arg:
                old = self.config.model
                self.config.model = arg.strip()
                self.llm.model = arg.strip()
                return f"Model changed: {old} -> {arg.strip()}"
            return f"Current model: {self.config.model}"

        if command == "/help":
            return (
                "Chat Commands:\n"
                "  /new [name]           Start a new conversation\n"
                "  /list                 List all conversations\n"
                "  /switch <name>        Switch to a conversation\n"
                "  /rename <old> <new>   Rename a conversation\n"
                "  /delete <name>        Delete a conversation\n"
                "  /clear                Clear current conversation\n"
                "  /export [name]        Export to markdown file\n"
                "  /model [name]         Show or change the model\n"
                "  /tasks                List scheduled tasks\n"
                "  /task_add n|h|p       Schedule a recurring task\n"
                "  /task_rm name         Remove a task\n"
                "  /help                 Show this help\n"
                "  /exit or /quit        Exit"
            )

        if command in ("/exit", "/quit"):
            return "__EXIT__"

        return None
