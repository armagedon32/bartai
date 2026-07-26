import json
from typing import Any, AsyncGenerator
from openai import OpenAI, AsyncOpenAI


class LLMClient:
    def __init__(self, config):
        self.client = OpenAI(
            base_url=config.openrouter_base_url,
            api_key=config.openrouter_api_key,
        )
        self.async_client = AsyncOpenAI(
            base_url=config.openrouter_base_url,
            api_key=config.openrouter_api_key,
        )
        self.model = config.model
        self.embedding_model = config.embedding_model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

    def chat_stream(self, messages: list[dict], tools: list[dict] | None = None):
        kwargs = dict(
            model=self.model,
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
            model=self.model,
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
            model=self.model,
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

    def embed(self, text: str) -> list[float]:
        resp = self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return resp.data[0].embedding
