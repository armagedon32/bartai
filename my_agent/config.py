import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_base_url = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.provider = os.getenv("AGENT_PROVIDER", "groq")  # openrouter or groq
        self.model = os.getenv("AGENT_MODEL", "openai/gpt-4o-mini")
        self.embedding_model = os.getenv("AGENT_EMBEDDING_MODEL", "text-embedding-3-small")
        self.max_turns = int(os.getenv("AGENT_MAX_TURNS", "30"))
        self.max_tool_retries = int(os.getenv("AGENT_MAX_TOOL_RETRIES", "5"))
        self.temperature = float(os.getenv("AGENT_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("AGENT_MAX_TOKENS", "2048"))
        self.data_dir = Path(os.getenv("AGENT_DATA_DIR", str(Path.home() / ".my_agent")))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.conv_dir = self.data_dir / "conversations"
        self.conv_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.data_dir / "tasks.json"
        self.system_prompt = os.getenv(
            "AGENT_SYSTEM_PROMPT",
            "You are BArt AI, an expert assistant. Use tools proactively when needed: web_search, web_fetch, execute_code (Python), create_chart, create_table, write_document, summarize, translate, research_topic, call_api, generate_image, search_memory, file_ops, system_info, install_package.\n"
            "Rules: Research before answering current events. Use execute_code for math/stats. Be concise. Format code with proper language tags.",
        )
