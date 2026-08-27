"""Vector store + hybrid search (dense cosine + sparse keyword overlap)."""

from __future__ import annotations

import threading

from .models import Chunk, Embedder, QueryResult, SearchReport, cosine, new_id, re_split


class VectorStore:
    """In-memory index with pluggable embedder. Swap for pgvector in prod;
    the interface (upsert/search) is what matters for portability."""

    def __init__(self, embedder: Embedder | None = None):
        self.embedder = embedder or Embedder()
        self._chunks: dict[str, Chunk] = {}
        self._lock = threading.Lock()

    def upsert(self, chunks: list[Chunk]) -> int:
        n = 0
        with self._lock:
            for c in chunks:
                c.embedding = self.embedder.embed(c.text)
                self._chunks[c.id] = c
                n += 1
        return n

    def __len__(self) -> int:
        return len(self._chunks)

    # ---- retrieval ------------------------------------------------------

    def dense_search(self, query: str, k: int = 5) -> list[QueryResult]:
        qv = self.embedder.embed(query)
        scored = [(QueryResult(c, cosine(qv, c.embedding)))   # type: ignore[arg-type]
                  for c in self._chunks.values()]
        scored.sort(key=lambda r: -r.score)
        return scored[:k]

    def keyword_search(self, query: str, k: int = 5) -> list[QueryResult]:
        qtoks = set(re_split(query))
        scored = []
        for c in self._chunks.values():
            ctoks = set(re_split(c.text))
            if not ctoks:
                continue
            overlap = len(qtoks & ctoks) / len(qtoks | ctoks)   # jaccard
            scored.append(QueryResult(c, overlap))
        scored.sort(key=lambda r: -r.score)
        return scored[:k]

    def hybrid_search(self, query: str, k: int = 5,
                      dense_weight: float = 0.6) -> list[QueryResult]:
        """RRF-style merge: dense catches meaning, keywords catch exact
        identifiers (SKU codes, error strings) that embeddings blur."""
        dense = self.dense_search(query, k * 3)
        kw = self.keyword_search(query, k * 3)

        scores: dict[str, float] = {}
        for rank, r in enumerate(dense):
            scores[r.chunk.id] = scores.get(r.chunk.id, 0) + \
                dense_weight / (60 + rank)
        for rank, r in enumerate(kw):
            scores[r.chunk.id] = scores.get(r.chunk.id, 0) + \
                (1 - dense_weight) / (60 + rank)

        by_id = {c.id: c for c in self._chunks.values()}
        merged = sorted(scores.items(), key=lambda kv: -kv[1])[:k]
        return [QueryResult(by_id[cid], s) for cid, s in merged]

    def search(self, query: str, k: int = 5,
               mode: str = "hybrid") -> SearchReport:
        import time
        t0 = time.perf_counter()
        fn = {"dense": self.dense_search,
              "keyword": self.keyword_search,
              "hybrid": self.hybrid_search}[mode]
        results = fn(query, k)
        ms = (time.perf_counter() - t0) * 1000
        cost = self.embedder.cost_usd(len(re_split(query)))
        return SearchReport(query=query, results=results, latency_ms=ms,
                            embedding_cost_usd=cost)


# re-export for ergonomics
__all__ = ["VectorStore", "new_id"]
