"""
Generate education policy docs, chunk them, and insert into UC table via SQL API for vector search indexing.

Usage:
    python execute_chunking.py --profile DEFAULT --warehouse-id <id> --catalog <catalog> --schema <schema>
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

# Import the edu policy doc generator from workspace scripts
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_SCRIPT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "workspace_setup_script")
sys.path.insert(0, WORKSPACE_SCRIPT_DIR)

from generate_edu_policy_docs import generate_docs, EDU_POLICY_DOCS

# Default output directory for generated docs
DEFAULT_DOCS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "edu_policy_docs")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def get_token(profile: str) -> str:
    result = subprocess.run(
        ["databricks", "auth", "token", "--profile", profile, "--output", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        print(f"ERROR: Failed to get auth token for profile '{profile}'.", file=sys.stderr)
        if result.stderr:
            print(f"  {result.stderr.strip()}", file=sys.stderr)
        print(f"\nFix: Run 'databricks auth login --profile {profile}' to authenticate.", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(result.stdout)["access_token"]
    except (json.JSONDecodeError, KeyError):
        print(f"ERROR: Unexpected response from 'databricks auth token':", file=sys.stderr)
        print(f"  {result.stdout[:200]}", file=sys.stderr)
        print(f"\nFix: Run 'databricks auth login --profile {profile}' to re-authenticate.", file=sys.stderr)
        sys.exit(1)


def get_host(profile: str) -> str:
    result = subprocess.run(
        ["databricks", "auth", "env", "--profile", profile, "--output", "json"],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            env_data = json.loads(result.stdout)
            return env_data.get("env", {}).get("DATABRICKS_HOST", "").rstrip("/")
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: try profiles list
    result = subprocess.run(
        ["databricks", "auth", "profiles", "--output", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        print(f"ERROR: Could not determine workspace host for profile '{profile}'.", file=sys.stderr)
        print(f"Fix: Run 'databricks auth login --profile {profile}'.", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(result.stdout)
        profiles = data.get("profiles", data) if isinstance(data, dict) else data
        for p in profiles:
            if p.get("name") == profile:
                return p.get("host", "").rstrip("/")
    except (json.JSONDecodeError, KeyError):
        pass
    print(f"ERROR: Profile '{profile}' not found. Available profiles:", file=sys.stderr)
    print(f"  Run 'databricks auth profiles' to see available profiles.", file=sys.stderr)
    sys.exit(1)


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
    parser = argparse.ArgumentParser(
        description="Generate education policy docs and insert into UC table for vector search indexing."
    )
    parser.add_argument("--profile", default="DEFAULT", help="Databricks CLI profile name")
    parser.add_argument("--warehouse-id", required=True, help="SQL warehouse ID")
    parser.add_argument("--catalog", required=True, help="Unity Catalog name (e.g. my_catalog)")
    parser.add_argument("--schema", required=True, help="Schema name (e.g. edupath_agent)")
    args = parser.parse_args()

    full_schema = f"{args.catalog}.{args.schema}"
    target_table = f"{full_schema}.policy_docs_chunked"

    token = get_token(args.profile)
    host = get_host(args.profile)
    wid = args.warehouse_id

    print(f"Host: {host}")
    print(f"Target table: {target_table}")

    # Generate education policy documents
    print(f"\nGenerating education policy documents...")
    docs_dir = generate_docs(DEFAULT_DOCS_DIR)
    print(f"  Created {len(EDU_POLICY_DOCS)} policy documents in: {docs_dir}")

    # Create table
    exec_sql(f"""
        CREATE OR REPLACE TABLE {target_table} (
            chunk_id STRING,
            doc_name STRING,
            content STRING
        )
    """, token, host, wid, "Create table")

    # Read and chunk docs
    all_rows = []
    print(f"\nReading and chunking policy documents from: {docs_dir}")
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(docs_dir, filename)
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
        stmt = f"INSERT INTO {target_table} (chunk_id, doc_name, content) VALUES {values}"
        exec_sql(stmt, token, host, wid, f"Batch {i//20 + 1}/{(len(all_rows)-1)//20 + 1}")

    print(f"\nDone! Wrote {len(all_rows)} chunks to {target_table}")


if __name__ == "__main__":
    main()
