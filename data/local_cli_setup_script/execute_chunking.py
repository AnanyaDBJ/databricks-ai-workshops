"""
Chunk local policy docs and insert into UC table via SQL API for vector search indexing.

Usage:
    python synthetic_data/execute_chunking.py --profile DEFAULT --warehouse-id <id>
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

CATALOG = "ananyaroy"
SCHEMA = "retail_wiab"
FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"
TARGET_TABLE = f"{FULL_SCHEMA}.policy_docs_chunked"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "verticals", "retail", "docs")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def get_token(profile: str) -> str:
    result = subprocess.run(
        ["databricks", "auth", "token", "--profile", profile, "-o", "json"],
        capture_output=True, text=True,
    )
    return json.loads(result.stdout)["access_token"]


def get_host(profile: str) -> str:
    result = subprocess.run(
        ["databricks", "auth", "profiles", "-o", "json"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    profiles = data.get("profiles", data) if isinstance(data, dict) else data
    for p in profiles:
        if p.get("name") == profile:
            return p.get("host", "")
    return ""


def run_sql(statement: str, token: str, host: str, warehouse_id: str) -> dict:
    payload = json.dumps({
        "warehouse_id": warehouse_id,
        "statement": statement,
        "wait_timeout": "50s",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/2.0/sql/statements",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  HTTP {e.code}: {body[:500]}", file=sys.stderr)
        return {"status": {"state": "FAILED"}}
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return {"status": {"state": "FAILED"}}

    state = data.get("status", {}).get("state", "")
    stmt_id = data.get("statement_id", "")
    poll_count = 0
    while state == "PENDING" and stmt_id and poll_count < 30:
        time.sleep(2)
        poll_count += 1
        poll_req = urllib.request.Request(
            f"{host}/api/2.0/sql/statements/{stmt_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(poll_req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                state = data.get("status", {}).get("state", "")
        except Exception:
            break
    return data


def exec_sql(stmt, token, host, wid, label=""):
    data = run_sql(stmt, token, host, wid)
    state = data.get("status", {}).get("state", "UNKNOWN")
    err = data.get("status", {}).get("error", {}).get("message", "")
    if label:
        print(f"  {label}: {state}" + (f" - {err}" if err else ""))
    return state


def chunk_text(text: str) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

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
                words = para.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= CHUNK_SIZE:
                        current = f"{current} {word}" if current else word
                    else:
                        chunks.append(current.strip())
                        overlap_text = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
                        current = f"{overlap_text} {word}"
            else:
                if chunks:
                    prev = chunks[-1]
                    overlap_text = prev[-CHUNK_OVERLAP:] if len(prev) > CHUNK_OVERLAP else prev
                    current = f"{overlap_text}\n\n{para}"
                else:
                    current = para

    if current.strip():
        chunks.append(current.strip())
    return chunks


def esc(s):
    return s.replace("'", "''").replace("\\", "\\\\")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="DEFAULT")
    parser.add_argument("--warehouse-id", required=True)
    args = parser.parse_args()

    token = get_token(args.profile)
    host = get_host(args.profile)
    wid = args.warehouse_id

    print(f"Host: {host}")
    print(f"Docs dir: {DOCS_DIR}")

    # Create table
    exec_sql(f"""
        CREATE OR REPLACE TABLE {TARGET_TABLE} (
            chunk_id STRING,
            doc_name STRING,
            content STRING
        )
    """, token, host, wid, "Create table")

    # Read and chunk docs
    all_rows = []
    for filename in sorted(os.listdir(DOCS_DIR)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, "r") as f:
            content = f.read()

        doc_name = filename.replace(".md", "")
        chunks = chunk_text(content)
        print(f"  {filename}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{doc_name}::{i}".encode()).hexdigest()[:16]
            all_rows.append(f"('{chunk_id}', '{esc(doc_name)}', '{esc(chunk)}')")

    print(f"\nTotal chunks: {len(all_rows)}")

    # Insert in batches
    for i in range(0, len(all_rows), 20):
        batch = all_rows[i:i+20]
        values = ", ".join(batch)
        stmt = f"INSERT INTO {TARGET_TABLE} (chunk_id, doc_name, content) VALUES {values}"
        exec_sql(stmt, token, host, wid, f"Batch {i//20 + 1}/{(len(all_rows)-1)//20 + 1}")

    print(f"\nDone! Wrote {len(all_rows)} chunks to {TARGET_TABLE}")


if __name__ == "__main__":
    main()
