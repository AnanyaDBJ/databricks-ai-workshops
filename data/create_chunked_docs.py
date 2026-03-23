"""
Read policy documents from UC Volume, chunk them, and write to a Unity Catalog table
for vector search indexing.

Usage:
    Run as a Databricks notebook after uploading policy docs to the UC Volume.

Prerequisites:
    1. Upload policy docs to UC Volume:
       databricks fs cp ./synthetic_data/policy_docs/ dbfs:/Volumes/ananyaroy/retail_wiab/policy_docs/ --recursive --profile <profile>

Target table: <CATALOG>.<SCHEMA>.policy_docs_chunked
"""

import hashlib
import os

from pyspark.sql import SparkSession

# ── Config ──────────────────────────────────────────────────────────
CATALOG = "qsic_workshop_prep_catalog"
SCHEMA = "retail_agent"
FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/policy_docs"
TARGET_TABLE = f"{FULL_SCHEMA}.policy_docs_chunked"

CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks

spark = SparkSession.builder.getOrCreate()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count, respecting paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If a single paragraph exceeds chunk_size, split it
            if len(para) > chunk_size:
                words = para.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= chunk_size:
                        current_chunk = f"{current_chunk} {word}" if current_chunk else word
                    else:
                        chunks.append(current_chunk.strip())
                        # Start new chunk with overlap from previous
                        overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                        current_chunk = f"{overlap_text} {word}"
            else:
                # Start new chunk with overlap from previous chunk
                if chunks:
                    prev = chunks[-1]
                    overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                    current_chunk = f"{overlap_text}\n\n{para}"
                else:
                    current_chunk = para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def generate_chunk_id(doc_name: str, chunk_index: int) -> str:
    """Generate a deterministic chunk ID."""
    raw = f"{doc_name}::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


# ── Read and chunk documents ────────────────────────────────────────
print(f"Reading policy docs from {VOLUME_PATH}...")

rows = []
try:
    files = os.listdir(VOLUME_PATH)
except FileNotFoundError:
    # Try using dbutils if running in Databricks notebook
    files = [f.name for f in dbutils.fs.ls(f"dbfs:{VOLUME_PATH}")]  # noqa: F821

for filename in sorted(files):
    if not filename.endswith(".md"):
        continue

    filepath = os.path.join(VOLUME_PATH, filename)
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception:
        # Fallback for Databricks environment
        content = spark.read.text(f"dbfs:{VOLUME_PATH}/{filename}").collect()
        content = "\n".join([row.value for row in content])

    doc_name = filename.replace(".md", "")
    chunks = chunk_text(content)

    print(f"  {filename}: {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        rows.append({
            "chunk_id": generate_chunk_id(doc_name, i),
            "doc_name": doc_name,
            "content": chunk,
        })

print(f"\nTotal chunks: {len(rows)}")

# ── Write to Unity Catalog ──────────────────────────────────────────
df = spark.createDataFrame(rows)
df.write.mode("overwrite").saveAsTable(TARGET_TABLE)
print(f"Wrote {df.count()} chunks to {TARGET_TABLE}")
