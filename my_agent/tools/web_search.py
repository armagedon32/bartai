import requests
from bs4 import BeautifulSoup
from my_agent.tools.registry import Tool

try:
    from ddgs import DDGS
    _ddgs = DDGS()
except ImportError:
    _ddgs = None


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web for information. Returns a list of results with titles, URLs, and snippets."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default 5)",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, num_results: int = 5) -> str:
        if _ddgs is None:
            return "Search unavailable: duckduckgo_search library not installed."

        try:
            results = list(_ddgs.text(query, max_results=num_results))
            if not results:
                return "No results found."

            output = []
            for r in results:
                title = r.get("title", "").strip()
                href = r.get("href", "")
                snippet = r.get("body", "").strip()
                output.append(f"- {title}\n  {href}\n  {snippet[:300]}")

            return "\n\n".join(output)
        except Exception as e:
            return f"Search failed: {e}"


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch and read the content of a web page. Returns the text content."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
        },
        "required": ["url"],
    }

    def execute(self, url: str) -> str:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if l.strip()]
            content = "\n".join(lines[:200])
            if len(lines) > 200:
                content += "\n\n... (content truncated)"
            return content
        except Exception as e:
            return f"Failed to fetch {url}: {e}"