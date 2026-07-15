#!/usr/bin/env python3
"""Local CLI workshop setup — laptop counterpart to the workspace notebook.

Runs the *same* shared logic as ``workspace_setup_script/01_quickstart_setup.py``
but writes via the SQL Statement Execution REST API instead of Spark, so it can
run from a laptop with only the Databricks CLI configured (no cluster).

Full parity with the notebook:
  1. Catalog + schema
  2. Industry structured tables   (lib.generate -> verticals/*/tables.py)
  3. Chunked policy/news docs      (lib.chunking.build_chunk_table)
  4. Vector Search endpoint+index  (lib.provisioning)
  5. Genie Space                   (lib.provisioning)
  6. MLflow experiment + UC fn     (lib.provisioning)

Usage:
    python local_cli_setup_script/setup.py \
        --industry retail --catalog my_catalog --schema my_schema \
        --profile DEFAULT

    # The first available SQL warehouse is auto-detected (a running one is
    # preferred). Pass --warehouse-id <id> only to pin a specific warehouse.

    # data-only (skip the SDK-backed steps):
    python local_cli_setup_script/setup.py --industry retail \
        --catalog c --schema s \
        --skip-vector-search --skip-genie --skip-mlflow
"""

import argparse
import os
import sys

# Make the data/ package importable (lib.*, verticals.*) regardless of cwd.
_DATA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DATA_ROOT not in sys.path:
    sys.path.insert(0, _DATA_ROOT)

from lib.chunking import build_chunk_table
from lib.generate import INDUSTRIES, SqlTableWriter, generate_workshop_data


def main():
    p = argparse.ArgumentParser(description="Local CLI workshop setup (SQL REST API).")
    p.add_argument("--industry", required=True, choices=INDUSTRIES)
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--profile", default="DEFAULT")
    p.add_argument(
        "--warehouse-id",
        default=None,
        help="SQL warehouse ID. If omitted, the first available warehouse is auto-detected.",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--skip-vector-search", action="store_true")
    p.add_argument("--skip-genie", action="store_true")
    p.add_argument("--skip-mlflow", action="store_true")
    args = p.parse_args()

    full_schema = f"{args.catalog}.{args.schema}"
    writer = SqlTableWriter.from_profile(args.profile, args.warehouse_id)
    print(f"Host: {writer.host}")
    print(f"SQL warehouse: {writer.warehouse_id}")
    print(f"Industry: {args.industry}  |  Target: {full_schema}\n")

    # ── Step 1: Catalog + schema ────────────────────────────────────────
    print("=== Step 1: Catalog and schema ===")
    writer.exec_sql(f"CREATE CATALOG IF NOT EXISTS {args.catalog}")
    writer.exec_sql(f"CREATE SCHEMA IF NOT EXISTS {full_schema}")

    # ── Step 2: Structured tables ───────────────────────────────────────
    print("\n=== Step 2: Structured data tables ===")
    workshop = generate_workshop_data(
        industry=args.industry,
        catalog=args.catalog,
        schema=args.schema,
        writer=writer,
        seed=args.seed,
    )

    # ── Step 3: Chunked docs ────────────────────────────────────────────
    print("\n=== Step 3: Chunked documents ===")
    chunk_table = build_chunk_table(workshop.docs_dir, target_table=workshop.chunk_table_name)
    writer.write_table(full_schema, chunk_table)

    # ── Steps 4-6: SDK-backed provisioning ──────────────────────────────
    vs_index_name = None
    genie_space_id = None
    experiment_name = experiment_id = None

    w = writer.w  # the SqlTableWriter owns the WorkspaceClient

    if not args.skip_vector_search:
        print("\n=== Step 4: Vector Search endpoint and index ===")
        from databricks.ai_search.client import AISearchClient
        from lib.provisioning import ensure_vector_search_index

        vsc = AISearchClient(
            workspace_url=writer.host,
            personal_access_token=writer.token,
            disable_notice=True,
        )
        vs_index_name = ensure_vector_search_index(
            w,
            writer,
            endpoint_name=workshop.vs_endpoint_name,
            full_schema=full_schema,
            chunk_table=workshop.chunk_table_name,
            index_name=workshop.doc_index_name,
            vector_search_client=vsc,
            org_id=None,
        )

    if not args.skip_genie:
        print("\n=== Step 5: Genie Space ===")
        from lib.provisioning import ensure_genie_space

        genie_space_id = ensure_genie_space(
            w,
            title=workshop.genie_title,
            description=workshop.genie_description,
            table_identifiers=[f"{full_schema}.{t}" for t in workshop.tables],
            warehouse_id=writer.warehouse_id,
            org_id=None,
        )

    if not args.skip_mlflow:
        print("\n=== Step 6: MLflow experiment ===")
        from lib.provisioning import ensure_mlflow_experiment

        username = w.current_user.me().user_name
        experiment_name, experiment_id = ensure_mlflow_experiment(
            suffix=workshop.mlflow_experiment_suffix,
            username=username,
            tracking_uri=f"databricks://{args.profile}",
            host=writer.host,
        )

    # Optional UC function always runs via the writer (SQL warehouse).
    print("\n=== Optional UC function ===")
    from lib.provisioning import register_optional_udf

    register_optional_udf(
        writer,
        udf_sql=workshop.optional_udf_sql,
        udf_name=workshop.optional_udf_name,
        full_schema=full_schema,
        host=writer.host,
    )

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"  {workshop.brand_name.upper()} WORKSHOP SETUP COMPLETE")
    print("=" * 70)
    print(f"  Catalog/Schema:          {full_schema}")
    print(f"  Tables:                  {', '.join(workshop.tables)}")
    print(f"  Chunk table:             {full_schema}.{workshop.chunk_table_name}")
    if vs_index_name:
        print(f"  Vector Search endpoint:  {workshop.vs_endpoint_name}")
        print(f"  Vector Search index:     {vs_index_name}")
    if genie_space_id:
        print(f"  Genie Space ID:          {genie_space_id}")
    if experiment_id:
        print(f"  MLflow experiment:       {experiment_name} (ID: {experiment_id})")
    if workshop.optional_udf_name:
        print(f"  UC function:             {full_schema}.{workshop.optional_udf_name}")
    print("=" * 70)


if __name__ == "__main__":
    main()
