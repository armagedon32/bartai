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
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
        self.provider = os.getenv("AGENT_PROVIDER", "gemini")  # gemini, groq, or openrouter
        self.model = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
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
            "You are BArt AI, an expert assistant with access to tools.\n\n"
            "Available tools: web_search, web_fetch, execute_code (Python), create_chart, create_table, "
            "write_document, summarize, translate, rephrase, check_writing, research_topic, call_api, "
            "generate_image, search_memory, file_ops, system_info, install_package.\n\n"
            "Rules:\n"
            "- Research before answering current events\n"
            "- Use execute_code for math, stats, or data analysis\n"
            "- Provide thorough, complete responses with proper formatting\n"
            "- When unsure, use tools to verify before responding",
        )
