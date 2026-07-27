import json
from typing import Any, AsyncGenerator
from openai import OpenAI, AsyncOpenAI


class LLMClient:
    def __init__(self, config):
        self.model = config.model
        self.embedding_model = config.embedding_model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

        # Auto-fallback kung walang Groq key
        if config.provider == "groq" and not config.groq_api_key:
            self.provider = "openrouter"
        else:
            self.provider = config.provider

        if self.provider == "groq":
            base_url = config.groq_base_url
            api_key = config.groq_api_key
        else:
            base_url = config.openrouter_base_url
            api_key = config.openrouter_api_key

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.async_client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    def _model_for_provider(self):
        if self.provider == "groq":
            model_map = {
                "openai/gpt-4o-mini": "llama-3.1-8b-instant",
                "openai/gpt-4o": "llama-3.3-70b-versatile",
                "openai/o3-mini": "mixtral-8x7b-32768",
                "anthropic/claude-3.5-sonnet": "llama-3.3-70b-versatile",
                "google/gemini-2.0-flash-001": "llama-3.1-8b-instant",
                "meta-llama/llama-4-scout": "llama-3.1-8b-instant",
                "deepseek/deepseek-chat": "deepseek-r1-distill-llama-70b",
                "google/gemini-1.5-flash": "llama-3.1-8b-instant",
            }
            return model_map.get(self.model, "llama-3.1-8b-instant")
        return self.model

    def chat_stream(self, messages: list[dict], tools: list[dict] | None = None):
        kwargs = dict(
            model=self._model_for_provider(),
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        if tools:
            kwargs["tools"] = tools
        return self.client.chat.completions.create(**kwargs)

    async def chat_stream_async(self, messages: list[dict], tools: list[dict] | None = None):
        kwargs = dict(
            model=self._model_for_provider(),
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        if tools:
            kwargs["tools"] = tools
        return await self.async_client.chat.completions.create(**kwargs)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict[str, Any]:
        kwargs = dict(
            model=self._model_for_provider(),
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
        response = self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        result = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return result

    def _embedding_model_for_provider(self):
        if self.provider == "groq":
            return "nomic-embed-text-v1.5"
        return self.embedding_model

    def embed(self, text: str) -> list[float]:
        resp = self.client.embeddings.create(
            model=self._embedding_model_for_provider(),
            input=text,
        )
        return resp.data[0].embedding
