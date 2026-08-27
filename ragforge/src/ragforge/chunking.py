"""Structure-aware chunking strategies and their measured trade-offs.

The lazy default is a fixed 512-token window; it cuts sentences in half
and orphans table rows. These strategies keep structure intact so the
retriever can match on meaning instead of luck. Each returns chunks with
heading provenance so answers can cite section context.
"""

from __future__ import annotations

import re

from .models import Chunk, Document, sha


def fixed_window(doc: Document, size_chars: int = 1600, overlap: int = 200) -> list[Chunk]:
    """The naive baseline everyone ships first."""
    chunks = []
    step = size_chars - overlap
    for i, start in enumerate(range(0, max(1, len(doc.text)), step)):
        piece = doc.text[start:start + size_chars]
        if not piece.strip():
            continue
        chunks.append(Chunk(
            id=sha(f"{doc.doc_id}:{i}"), doc_id=doc.doc_id, text=piece,
            start_char=start, end_char=start + len(piece),
        ))
    return chunks


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def markdown_aware(doc: Document, target_chars: int = 1200) -> list[Chunk]:
    """Split on heading boundaries; keep each section whole when it fits.

    Sections smaller than the target stay single chunks. Oversized
    sections fall back to paragraph packing inside the section, so a
    giant section never becomes one unmatchable blob.
    """
    matches = list(_HEADING_RE.finditer(doc.text))
    sections: list[tuple[list[str], int, int]] = []
    if not matches:
        return fixed_window(doc, target_chars * 4 // 3)

    # preamble before first heading
    if matches[0].start() > 0:
        sections.append((["(preamble)"], 0, matches[0].start()))

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(doc.text)
        level = len(m.group(1))
        title = m.group(2).strip()
        # build heading path by scanning backwards for nearest shallower heading
        path = [title]
        for prev in reversed(matches[:i]):
            plen = len(prev.group(1))
            if plen < level:
                path.insert(0, prev.group(2).strip())
                level = plen
            if level <= 1:
                break
        sections.append((path, m.start(), end))

    chunks: list[Chunk] = []
    for path, s, e in sections:
        body = doc.text[s:e].strip()
        if not body:
            continue
        if len(body) <= target_chars * 1.25:
            chunks.append(Chunk(
                id=sha(f"{doc.doc_id}:{s}:{body[:40]}"), doc_id=doc.doc_id,
                text=body, heading_path=path, start_char=s, end_char=e,
            ))
        else:
            # pack paragraphs within the section up to target size
            paras = [p for p in body.split("\n\n") if p.strip()]
            buf, buf_start = "", s
            offset = s
            for p in paras:
                if buf and len(buf) + len(p) > target_chars:
                    chunks.append(Chunk(
                        id=sha(f"{doc.doc_id}:{buf_start}:{buf[:40]}"),
                        doc_id=doc.doc_id, text=buf.strip(),
                        heading_path=path, start_char=buf_start,
                        end_char=offset,
                    ))
                    buf, buf_start = "", offset
                if not buf:
                    buf_start = offset
                buf += p + "\n\n"
                offset += len(p) + 2
            if buf.strip():
                chunks.append(Chunk(
                    id=sha(f"{doc.doc_id}:{buf_start}:{buf[:40]}"),
                    doc_id=doc.doc_id, text=buf.strip(), heading_path=path,
                    start_char=buf_start, end_char=offset,
                ))
    return chunks
