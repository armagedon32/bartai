import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from my_agent.tools.registry import Tool

try:
    from ddgs import DDGS
    _ddgs_research = DDGS()
except ImportError:
    _ddgs_research = None


class ResearchTool(Tool):
    name = "research_topic"
    description = "Deep research on any topic. Searches multiple queries, reads top sources, and synthesizes findings into a structured summary. Use for in-depth investigation, competitive analysis, academic research, fact-checking, or learning about unfamiliar topics across any field (science, technology, business, medicine, law, arts, history, etc.)."
    parameters = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic or question to research thoroughly.",
            },
            "depth": {
                "type": "string",
                "enum": ["quick", "standard", "deep"],
                "description": "Research depth. 'quick' = 3 searches, 'standard' = 5 searches, 'deep' = 8 searches with more sources.",
            },
        },
        "required": ["topic"],
    }

    def execute(self, topic: str, depth: str = "standard") -> str:
        try:
            num_queries = {"quick": 2, "standard": 3, "deep": 5}[depth]
            num_results = {"quick": 3, "standard": 4, "deep": 6}[depth]

            queries = self._generate_queries(topic, num_queries)
            all_sources = []

            for query in queries:
                results = self._search(query, num_results)
                all_sources.extend(results)

            seen_urls = set()
            unique_sources = []
            for s in all_sources:
                if s["url"] not in seen_urls:
                    seen_urls.add(s["url"])
                    unique_sources.append(s)

            unique_sources = unique_sources[:15]

            fetched = []
            for src in unique_sources[:8]:
                content = self._fetch_page(src["url"], max_chars=3000)
                if content:
                    fetched.append({
                        "title": src["title"],
                        "url": src["url"],
                        "snippet": src["snippet"],
                        "content": content,
                    })

            result = [f"# Research: {topic}\n"]
            result.append(f"**Depth:** {depth} | **Sources consulted:** {len(fetched)}\n")

            if fetched:
                result.append("\n## Source Summaries\n")
                for i, src in enumerate(fetched, 1):
                    result.append(f"### {i}. {src['title']}")
                    result.append(f"**URL:** {src['url']}")
                    text = src["content"][:2000]
                    result.append(f"{text}\n")

            result.append("\n## Synthesis\n")
            result.append("Key findings from the research:\n")
            key_points = []
            for src in fetched:
                text = src["content"]
                sentences = [s.strip() for s in text.replace("\n", " ").split(".") if len(s.strip()) > 40][:3]
                key_points.extend(sentences)
            for i, pt in enumerate(key_points[:8], 1):
                result.append(f"{i}. {pt}.")
            result.append(f"\n\n*Research completed. {len(unique_sources)} sources found, {len(fetched)} read in full.*")

            return "\n".join(result)

        except Exception as e:
            return f"Research error: {e}"

    def _generate_queries(self, topic: str, n: int) -> list:
        base_queries = [topic, f"what is {topic}", f"{topic} overview"]
        if n >= 2:
            base_queries.append(f"{topic} examples")
            base_queries.append(f"{topic} latest developments 2026")
        if n >= 3:
            base_queries.append(f"{topic} explained simply")
            base_queries.append(f"{topic} applications")
        if n >= 4:
            base_queries.append(f"{topic} benefits and drawbacks")
            base_queries.append(f"{topic} future trends")
        if n >= 5:
            base_queries.append(f"{topic} key concepts")
            base_queries.append(f"{topic} comparison")
        return base_queries[:n]

    def _search(self, query: str, num: int) -> list:
        if _ddgs_research is None:
            return []
        try:
            raw = list(_ddgs_research.text(query, max_results=num))
            results = []
            for r in raw:
                results.append({
                    "title": r.get("title", "").strip(),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "").strip()[:300],
                })
            return results
        except Exception:
            return []

    def _fetch_page(self, url: str, max_chars: int = 3000) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            lines = [l for l in text.split("\n") if l.strip()]
            content = "\n".join(lines[:100])
            return content[:max_chars]
        except Exception:
            return ""


class SummarizeTool(Tool):
    name = "summarize"
    description = "Summarize long text, articles, documents, or web content. Extracts key points, main arguments, and conclusions. Use for digesting long content, extracting insights, or creating executive summaries."
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text content to summarize. Can be a long passage, article body, or document content.",
            },
            "max_points": {
                "type": "integer",
                "description": "Maximum number of key points to extract (default 5).",
            },
            "format": {
                "type": "string",
                "enum": ["bullet_points", "paragraph", "executive_summary"],
                "description": "Output format for the summary.",
            },
        },
        "required": ["text"],
    }

    def execute(self, text: str, max_points: int = 5, format: str = "bullet_points") -> str:
        if not text.strip():
            return "No text provided to summarize."
        word_count = len(text.split())
        char_count = len(text)
        header = f"**Summary** | {word_count} words, {char_count} chars | {format}\n\n"
        if format == "bullet_points":
            return header + f"Key points (up to {max_points}):\n[The AI should extract and list the key points here in its response based on the full conversation context.]"
        elif format == "executive_summary":
            return header + f"Executive Summary:\n[The AI should synthesize a concise executive summary here.]"
        else:
            return header + f"Summary:\n[The AI should write a coherent paragraph summary here.]"