import json
import numpy as np
from pathlib import Path


class MemoryIndex:
    def __init__(self, data_dir: str, embed_fn=None):
        self.index_path = Path(data_dir) / "memory_index.json"
        self.embed_fn = embed_fn
        self.chunks: list[dict] = []
        self.embeddings: list[list[float]] = []
        self._load()

    def _load(self):
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                self.chunks = data.get("chunks", [])
                self.embeddings = data.get("embeddings", [])
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _save(self):
        self.index_path.write_text(
            json.dumps({"chunks": self.chunks, "embeddings": self.embeddings}, indent=2),
            encoding="utf-8",
        )

    def add_text(self, text: str, metadata: dict | None = None):
        if not text.strip():
            return
        self.chunks.append({"text": text[:1000], "metadata": metadata or {}})
        if self.embed_fn:
            emb = self.embed_fn(text[:1000])
            self.embeddings.append(emb)
        self._save()

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.embeddings and self.embed_fn:
            return self._search_vector(query, top_k)
        return self._search_keyword(query, top_k)

    def _search_vector(self, query: str, top_k: int) -> list[dict]:
        q_emb = self.embed_fn(query)
        scores = []
        for i, emb in enumerate(self.embeddings):
            sim = float(np.dot(q_emb, emb))
            scores.append((sim, i))
        scores.sort(reverse=True)
        results = []
        for sim, idx in scores[:top_k]:
            results.append({
                "score": round(sim, 3),
                "text": self.chunks[idx]["text"],
                "metadata": self.chunks[idx].get("metadata", {}),
            })
        return results

    def _search_keyword(self, query: str, top_k: int) -> list[dict]:
        words = set(query.lower().split())
        scored = []
        for i, chunk in enumerate(self.chunks):
            text = chunk["text"].lower()
            score = sum(1 for w in words if w in text)
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        results = []
        for score, idx in scored[:top_k]:
            results.append({
                "score": score,
                "text": self.chunks[idx]["text"],
                "metadata": self.chunks[idx].get("metadata", {}),
            })
        return results
