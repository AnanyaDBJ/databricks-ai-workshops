"""Chunk policy markdown into policy_docs_chunked for Vector Search."""

import hashlib
import os

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


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


def chunk_policy_docs_to_table(spark, full_schema: str, docs_dir: str) -> int:
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Policy docs not found: {docs_dir}")

    all_chunks = []
    print(f"Reading policy documents from: {docs_dir}\n")
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

    df = spark.createDataFrame(all_chunks)
    df.write.mode("overwrite").saveAsTable(f"{full_schema}.policy_docs_chunked")
    print(f"\nCreated {full_schema}.policy_docs_chunked — {df.count()} chunks")
    return df.count()
