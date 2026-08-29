# ragforge

**Structure-aware RAG that shows you, with numbers, why the lazy 512-token window loses answers.**

Every RAG demo chunks by character count and hopes. ragforge chunks on markdown structure, keeps section provenance, and runs hybrid dense-plus-keyword search. The honest part: it ships a `SearchReport` that proves which strategy retrieved the answer and which one missed it, so you can defend the architecture instead of guessing.

## Why this is the room incumbents abstract away

Vector stores sell you "semantic search" and hide the retrieval numbers. ragforge makes retrieval auditable: every query returns a `SearchReport` with the chunk, its section, the score, and whether it actually contained the answer. The interview question this answers is the one most candidates flub: does your chunking strategy change retrieval quality, and can you prove it?

## What it actually does

- **Document / Chunk**: a doc splits into chunks that carry their markdown section as provenance.
- **fixed_window vs markdown_aware**: two chunkers you can A/B in one line.
- **Embedder**: a deterministic bag-of-words embedder (no external model needed to run).
- **VectorStore**: hybrid dense + keyword search over chunks.
- **SearchReport**: the receipts, per query, for what retrieved and what did not.

## Quickstart

```bash
pip install -e "./ragforge"

from ragforge import Document, fixed_window, markdown_aware, VectorStore, Embedder

doc = Document(doc_id="handbook", text=open("handbook.md").read())
store = VectorStore()
emb = Embedder()
for c in markdown_aware(doc):        # or fixed_window(doc, size=512)
    store.add(c, emb.embed(c.text))

report = store.search("refund policy", emb.embed("refund policy"), k=3)
print(report.found, report.chunks)   # found=True and the section it came from
```

## Quality (measured)

| Signal | Value |
|---|---|
| Tests | 6 green (chunking, hybrid search, retrieval report) |
| Ruff | clean |
| Mypy | clean |
| Bandit | clean (sha256 content hashing, no weak hashes) |

Run: `pytest ragforge/tests/ -q`

## Honest limitations

- The default `Embedder` is a deterministic baseline so the package runs with zero external dependencies. Swap in a real embedding model for production semantic search; the store and report layers do not care which embedder you use.
- `SearchReport` measures retrieval, not answer quality. Pair it with evalforge for end-to-end answer grading.

## License

MIT.
