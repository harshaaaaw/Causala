"""Core models for ragforge."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field


def sha(obj) -> str:
    if not isinstance(obj, str):
        obj = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(obj.encode()).hexdigest()[:16]


@dataclass
class Document:
    doc_id: str
    text: str
    meta: dict = field(default_factory=dict)


@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str
    heading_path: list[str] = field(default_factory=list)
    start_char: int = 0
    end_char: int = 0
    embedding: list[float] | None = None   # injected by an Embedder


@dataclass
class QueryResult:
    chunk: Chunk
    score: float


@dataclass
class SearchReport:
    query: str
    results: list[QueryResult]
    latency_ms: float
    embedding_cost_usd: float = 0.0


class Embedder:
    """Interface over any embedding backend. The hash embedder is a
    deterministic bag-of-words stand-in so tests and demos run offline;
    swap in Voyage/OpenAI/pgvector-serving models for real retrieval."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        import math
        vec = [0.0] * self.dim
        for tok in re_split(text):
            h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def cost_usd(self, n_tokens: int) -> float:
        return 0.0  # offline embedder is free; real ones plug their pricing here


def re_split(text: str) -> list[str]:
    out, buf = [], []
    for ch in text.lower():
        if ch.isalnum():
            buf.append(ch)
        elif buf:
            out.append("".join(buf))
            buf = []
    if buf:
        out.append("".join(buf))
    return out


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def now() -> float:
    return time.time()
