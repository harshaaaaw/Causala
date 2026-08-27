"""ragforge: retrieval that earns the numbers it reports."""

from .chunking import fixed_window, markdown_aware
from .models import Chunk, Document, Embedder, QueryResult, SearchReport, sha
from .store import VectorStore

__version__ = "1.0.0"

__all__ = [
    "Chunk", "Document", "Embedder", "QueryResult", "SearchReport",
    "VectorStore", "fixed_window", "markdown_aware", "sha",
]
