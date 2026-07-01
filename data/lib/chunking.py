"""Chunk markdown into a Unity Catalog table for Vector Search.

Spark-free: :func:`build_chunk_table` reads and chunks the markdown into a
``TableData`` payload; the caller persists it with ``writer.write_table``.
"""

import hashlib
import os

from verticals.base import TableData

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

CHUNK_COLUMNS = [
    ("chunk_id", "STRING"),
    ("doc_name", "STRING"),
    ("content", "STRING"),
]


def chunk_text(text: str) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks, current = [], ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= CHUNK_SIZE:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            if len(para) > CHUNK_SIZE:
                words, current = para.split(), ""
                for word in words:
                    if len(current) + len(word) + 1 <= CHUNK_SIZE:
                        current = f"{current} {word}" if current else word
                    else:
                        chunks.append(current.strip())
                        overlap = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
                        current = f"{overlap} {word}"
            else:
                if chunks:
                    prev = chunks[-1]
                    overlap = prev[-CHUNK_OVERLAP:] if len(prev) > CHUNK_OVERLAP else prev
                    current = f"{overlap}\n\n{para}"
                else:
                    current = para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def build_chunk_table(
    docs_dir: str,
    target_table: str = "policy_docs_chunked",
) -> TableData:
    """Read and chunk every ``.md`` in ``docs_dir`` into a ``TableData`` (no Spark)."""
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")

    all_chunks = []
    print(f"Reading documents from: {docs_dir}\n")
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        with open(os.path.join(docs_dir, filename), encoding="utf-8") as f:
            content = f.read()
        doc_name = filename.replace(".md", "")
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "chunk_id": hashlib.md5(f"{doc_name}::{i}".encode()).hexdigest()[:16],
                "doc_name": doc_name,
                "content": chunk,
            })
        print(f"  {filename}: {len(chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")
    return TableData(name=target_table, columns=CHUNK_COLUMNS, rows=all_chunks)
