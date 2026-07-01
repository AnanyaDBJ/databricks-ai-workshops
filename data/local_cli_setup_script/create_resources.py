"""
Create Databricks resources (Vector Search endpoint/index + Genie Space) via REST API.
Run this after generating the data tables and chunked docs.

Usage:
    python create_resources.py --profile DEFAULT --warehouse-id <id> --catalog <catalog> --schema <schema>

Examples:
    python create_resources.py --warehouse-id 9a7b09e77b8a8994 --catalog my_catalog --schema retail_agent
    python create_resources.py --warehouse-id abc123 --catalog demo --schema workshop --vs-endpoint-name my-endpoint
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import subprocess


# ── Auth helpers ───────────────────────────────────────────────────────

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
            host = env_data.get("env", {}).get("DATABRICKS_HOST", "").rstrip("/")
            if host:
                return host
        except (json.JSONDecodeError, KeyError):
            pass

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
    print(f"ERROR: Profile '{profile}' not found.", file=sys.stderr)
    print(f"  Run 'databricks auth profiles' to see available profiles.", file=sys.stderr)
    sys.exit(1)


# ── REST API helpers ───────────────────────────────────────────────────

def api_request(method: str, url: str, token: str, body: dict = None, timeout: int = 60) -> dict:
    """Make a REST API request and return the JSON response."""
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8")
        try:
            return {"_error": True, "_status": e.code, **json.loads(resp_body)}
        except json.JSONDecodeError:
            return {"_error": True, "_status": e.code, "_body": resp_body[:500]}
    except Exception as e:
        return {"_error": True, "_status": 0, "_body": str(e)}


def run_sql(statement: str, token: str, host: str, warehouse_id: str) -> dict:
    """Execute SQL via REST API with polling."""
    payload = json.dumps({
        "warehouse_id": warehouse_id,
        "statement": statement,
        "wait_timeout": "50s",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/2.0/sql/statements",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
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


# ── Vector Search ──────────────────────────────────────────────────────

def create_vs_endpoint(host: str, token: str, endpoint_name: str) -> bool:
    """Create a Vector Search endpoint. Returns True if created/exists."""
    print(f"\n{'=' * 60}")
    print(f"Step 1: Vector Search Endpoint '{endpoint_name}'")
    print("=" * 60)

    # Check if it already exists
    resp = api_request("GET", f"{host}/api/2.0/vector-search/endpoints/{endpoint_name}", token)
    if not resp.get("_error"):
        state = resp.get("endpoint_status", {}).get("state", "UNKNOWN")
        print(f"  Endpoint already exists (state: {state})")
        if state == "ONLINE":
            return True
        print(f"  Waiting for endpoint to come ONLINE...")
    else:
        status_code = resp.get("_status", 0)
        if status_code == 404:
            print(f"  Creating endpoint '{endpoint_name}'...")
            create_resp = api_request("POST", f"{host}/api/2.0/vector-search/endpoints", token, body={
                "name": endpoint_name,
                "endpoint_type": "STANDARD",
            })
            if create_resp.get("_error"):
                print(f"  ERROR: Failed to create endpoint: {create_resp}", file=sys.stderr)
                return False
            print(f"  Endpoint creation initiated.")
        else:
            print(f"  ERROR: Unexpected response checking endpoint: {resp}", file=sys.stderr)
            return False

    # Poll until ONLINE (up to 10 minutes)
    print(f"  Waiting for endpoint to become ONLINE (this can take 5-10 minutes)...")
    for attempt in range(60):
        time.sleep(10)
        resp = api_request("GET", f"{host}/api/2.0/vector-search/endpoints/{endpoint_name}", token)
        state = resp.get("endpoint_status", {}).get("state", "UNKNOWN")
        if state == "ONLINE":
            print(f"  Endpoint is ONLINE!")
            return True
        if attempt % 6 == 0:
            print(f"  Still waiting... (state: {state}, elapsed: {(attempt + 1) * 10}s)")

    print(f"  WARNING: Endpoint did not reach ONLINE state within 10 minutes.", file=sys.stderr)
    print(f"  Check Databricks UI: Compute > Vector Search", file=sys.stderr)
    return False


def enable_cdf(host: str, token: str, warehouse_id: str, table_name: str) -> bool:
    """Enable Change Data Feed on the source table."""
    print(f"\n  Enabling Change Data Feed on '{table_name}'...")
    stmt = f"ALTER TABLE {table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
    result = run_sql(stmt, token, host, warehouse_id)
    state = result.get("status", {}).get("state", "UNKNOWN")
    if state in ("SUCCEEDED", "CLOSED"):
        print(f"  CDF enabled.")
        return True
    err = result.get("status", {}).get("error", {}).get("message", "")
    if "already enabled" in err.lower() or "DELTA_TABLE_PROPERTY_ALREADY_SET" in err:
        print(f"  CDF already enabled.")
        return True
    print(f"  WARNING: CDF enable returned state '{state}': {err}")
    return True


def create_vs_index(host: str, token: str, warehouse_id: str, endpoint_name: str,
                    index_name: str, source_table: str) -> bool:
    """Create a Delta Sync Vector Search index."""
    print(f"\n{'=' * 60}")
    print(f"Step 2: Vector Search Index '{index_name}'")
    print("=" * 60)

    # Check if index already exists
    resp = api_request("GET", f"{host}/api/2.0/vector-search/indexes/{index_name}", token)
    if not resp.get("_error"):
        state = resp.get("status", {}).get("ready", False)
        index_state = "READY" if state else "PROVISIONING"
        print(f"  Index already exists (state: {index_state})")
        return True

    # Enable CDF on the source table
    enable_cdf(host, token, warehouse_id, source_table)

    # Create the index
    print(f"  Creating Delta Sync index...")
    print(f"    Source table: {source_table}")
    print(f"    Endpoint: {endpoint_name}")
    print(f"    Embedding model: databricks-gte-large-en")

    create_resp = api_request("POST", f"{host}/api/2.0/vector-search/indexes", token, body={
        "name": index_name,
        "endpoint_name": endpoint_name,
        "primary_key": "chunk_id",
        "index_type": "DELTA_SYNC",
        "delta_sync_index_spec": {
            "source_table": source_table,
            "pipeline_type": "TRIGGERED",
            "embedding_source_columns": [
                {"name": "content", "embedding_model_endpoint_name": "databricks-gte-large-en"}
            ],
        },
    })

    if create_resp.get("_error"):
        error_code = create_resp.get("error_code", "")
        message = create_resp.get("message", str(create_resp))
        if "ALREADY_EXISTS" in error_code or "already exists" in message.lower():
            print(f"  Index already exists.")
            return True
        print(f"  ERROR: Failed to create index: {message}", file=sys.stderr)
        return False

    print(f"  Index creation initiated! It will sync in the background.")
    print(f"  You can monitor progress in: Catalog Explorer > {index_name}")
    return True


# ── Genie Space ────────────────────────────────────────────────────────

def create_genie_space(host: str, token: str, warehouse_id: str,
                       catalog: str, schema: str) -> str | None:
    """Create a Genie Space with the 6 retail tables. Returns the space ID."""
    print(f"\n{'=' * 60}")
    print("Step 3: Genie Space")
    print("=" * 60)

    space_title = f"FreshMart Retail Data ({schema})"
    tables = ["customers", "products", "stores", "transactions", "transaction_items", "payment_history"]
    table_identifiers = [f"{catalog}.{schema}.{t}" for t in tables]

    # Check if space already exists
    resp = api_request("GET", f"{host}/api/2.0/genie/spaces", token)
    if not resp.get("_error"):
        for space in resp.get("spaces", []):
            if space.get("title") == space_title:
                space_id = space.get("space_id")
                print(f"  Genie Space '{space_title}' already exists (ID: {space_id})")
                return space_id

    # Create the space
    print(f"  Creating Genie Space '{space_title}'...")
    print(f"    Tables: {', '.join(tables)}")
    print(f"    Warehouse: {warehouse_id}")

    serialized_space = json.dumps({
        "version": 2,
        "data_sources": {
            "tables": [{"identifier": t} for t in sorted(table_identifiers)]
        }
    })

    create_resp = api_request("POST", f"{host}/api/2.0/genie/spaces", token, body={
        "title": space_title,
        "description": f"FreshMart retail grocery data for natural language queries. "
                       f"Contains customer, product, store, transaction, and payment data.",
        "warehouse_id": warehouse_id,
        "serialized_space": serialized_space,
    })

    if create_resp.get("_error"):
        print(f"  ERROR: Failed to create Genie Space: {create_resp}", file=sys.stderr)
        return None

    space_id = create_resp.get("space_id")
    if space_id:
        print(f"  Genie Space created! (ID: {space_id})")
    else:
        print(f"  WARNING: Genie Space created but no space_id returned: {create_resp}")
    return space_id


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Create Vector Search endpoint/index and Genie Space for the FreshMart retail agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python create_resources.py --warehouse-id 9a7b09e77b8a8994 --catalog my_catalog --schema retail_agent
    python create_resources.py --warehouse-id abc123 --catalog demo --schema workshop --vs-endpoint-name my-vs
        """,
    )
    parser.add_argument("--profile", default="DEFAULT", help="Databricks CLI profile name (default: DEFAULT)")
    parser.add_argument("--warehouse-id", required=True, help="SQL warehouse ID (for Genie and SQL operations)")
    parser.add_argument("--catalog", required=True, help="Unity Catalog name (e.g. my_catalog)")
    parser.add_argument("--schema", required=True, help="Schema name (e.g. retail_agent)")
    parser.add_argument("--vs-endpoint-name", default=None,
                        help="Vector Search endpoint name (default: freshmart-vs-<schema>)")
    parser.add_argument("--vs-index-name", default="policy_docs_index",
                        help="Vector Search index name (default: policy_docs_index)")
    args = parser.parse_args()

    # Defaults
    vs_endpoint = args.vs_endpoint_name or f"freshmart-vs-{args.schema.replace('_', '-')}"
    vs_index_full = f"{args.catalog}.{args.schema}.{args.vs_index_name}"
    source_table = f"{args.catalog}.{args.schema}.policy_docs_chunked"

    # Auth
    print("Authenticating...")
    token = get_token(args.profile)
    host = get_host(args.profile)
    print(f"  Host: {host}")
    print(f"  Catalog: {args.catalog}")
    print(f"  Schema: {args.schema}")

    # Create resources
    vs_ok = create_vs_endpoint(host, token, vs_endpoint)
    if vs_ok:
        create_vs_index(host, token, args.warehouse_id, vs_endpoint, vs_index_full, source_table)

    genie_space_id = create_genie_space(host, token, args.warehouse_id, args.catalog, args.schema)

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    print(f"  Vector Search Endpoint: {vs_endpoint}")
    print(f"  Vector Search Index:    {vs_index_full}")
    if genie_space_id:
        print(f"  Genie Space ID:         {genie_space_id}")
    else:
        print(f"  Genie Space ID:         (failed - create manually in UI)")

    print(f"\nAdd these to your advanced/.env file:")
    print(f"  VECTOR_SEARCH_INDEX={vs_index_full}")
    if genie_space_id:
        print(f"  GENIE_SPACE_ID={genie_space_id}")
    print()


if __name__ == "__main__":
    main()
