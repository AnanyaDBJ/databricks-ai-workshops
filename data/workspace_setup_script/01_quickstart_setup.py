# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "1"
# ///
# MAGIC %md
# MAGIC    
# MAGIC # AI Workshop Data Setup
# MAGIC
# MAGIC This notebook creates everything you need for the workshop:
# MAGIC
# MAGIC | Step | What it creates |
# MAGIC |------|----------------|
# MAGIC | 1 | Catalog and schema in Unity Catalog |
# MAGIC | 2 | Industry-specific structured data tables (see **Industry** widget) |
# MAGIC | 3 | Policy documents table (chunked for search) |
# MAGIC | 4 | Vector Search endpoint and index |
# MAGIC | 5 | Genie Space for natural language data queries |
# MAGIC | 6 | MLflow experiment for agent evaluation |
# MAGIC
# MAGIC **Instructions:** Set **Industry**, **Catalog**, and **Schema** in the widgets, then click **Run All**.
# MAGIC
# MAGIC | Industry | Tables | Policy docs |
# MAGIC |----------|--------|-------------|
# MAGIC | `education` | 6 tables (students, courses, campuses, …) | EduPath Academy |
# MAGIC | `retail` | 6 tables (customers, products, stores, …) | FreshMart (`verticals/retail/docs/`) |
# MAGIC | `financial_services` | 6 tables (clients, accounts, trades, …) | Meridian Capital Partners |
# MAGIC
# MAGIC For `financial_services`, real market data (daily prices and company profiles, 29 tickers) ships with the repo as CSVs in `verticals/financial_services/market_data/` and is loaded into `{catalog}.{schema}` automatically — no Marketplace or Delta Sharing access needed.
# MAGIC
# MAGIC > **First run:** the Configuration cell below stops with an error until the widgets are filled in. Fill them, then click **Run All** again — the `%restart_python` above means later cells need the Configuration cell to have run in the same session.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC
# MAGIC Set your catalog and schema names using the widgets above. All workshop resources are created under `{catalog}.{schema}`.

# COMMAND ----------

# MAGIC %pip install databricks-ai-search
# MAGIC %restart_python

# COMMAND ----------

import sys


_notebook_path = dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get()
_data_root = "/Workspace" + "/".join(_notebook_path.split("/")[:-2])
if _data_root not in sys.path:
    sys.path.insert(0, _data_root)

from verticals.base import vs_endpoint_name
from verticals.registry import INDUSTRIES

if "industry" not in dbutils.widgets.getAll():
    dbutils.widgets.dropdown(
        "industry",
        "education",
        list(INDUSTRIES),
        "Industry",
    )
if "catalog" not in dbutils.widgets.getAll():
    dbutils.widgets.text("catalog", "", "Catalog Name")
if "schema" not in dbutils.widgets.getAll():
    dbutils.widgets.text("schema", "", "Schema Name")

INDUSTRY = dbutils.widgets.get("industry")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

if not CATALOG:
    raise ValueError(
        "Fill the Catalog widget at the top of the notebook, then click Run All again — "
        "later cells depend on this cell having run (a NameError on FULL_SCHEMA means it hasn't)."
    )
if not SCHEMA:
    raise ValueError(
        "Fill the Schema widget at the top of the notebook, then click Run All again — "
        "later cells depend on this cell having run (a NameError on FULL_SCHEMA means it hasn't)."
    )

if INDUSTRY not in INDUSTRIES:
    raise ValueError(f"Unknown industry '{INDUSTRY}'. Expected one of: {', '.join(INDUSTRIES)}")
PLANNED_VS_ENDPOINT_NAME = vs_endpoint_name(INDUSTRY, SCHEMA)

FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"
print(f"Industry: {INDUSTRY}")
print(f"Workshop tables: {FULL_SCHEMA}")
print(f"Planned Vector Search endpoint: {PLANNED_VS_ENDPOINT_NAME}")
if INDUSTRY == "financial_services":
    print(f"Market data (bundled CSVs in the repo) will be loaded into {FULL_SCHEMA}.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect: Workspace client and SQL warehouse
# MAGIC
# MAGIC This notebook writes all data through the SQL Statement Execution API (no Spark), so it needs a **SQL warehouse**. The first available warehouse is auto-discovered (a running one is preferred).

# COMMAND ----------

from databricks.sdk import WorkspaceClient

from lib.generate import SqlTableWriter
from lib.provisioning import _first_warehouse_id
from lib.workspace_links import notebook_org_id, workspace_host

w = WorkspaceClient()
WORKSPACE_HOST = workspace_host(w)
WORKSPACE_ORG_ID = notebook_org_id(dbutils)
WAREHOUSE_ID = _first_warehouse_id(w)
if not WAREHOUSE_ID:
    raise ValueError(
        "No SQL warehouse found. Start a SQL warehouse and click Run All again — "
        "this notebook writes via the SQL Statement Execution API."
    )

writer = SqlTableWriter(w, WAREHOUSE_ID)
print(f"Using SQL warehouse: {WAREHOUSE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Catalog and Schema

# COMMAND ----------

writer.exec_sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")  # Only if you have access to create catalog and want a new catalog for the workshop
writer.exec_sql(f"CREATE SCHEMA IF NOT EXISTS {FULL_SCHEMA}")
print(f"Catalog '{CATALOG}' and schema '{FULL_SCHEMA}' are ready.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Generate Industry Data Tables
# MAGIC
# MAGIC Uses the `data` package industry module. Table names and semantics depend on the **Industry** widget.

# COMMAND ----------

from lib.generate import generate_workshop_data

workshop = generate_workshop_data(
    industry=INDUSTRY,
    catalog=CATALOG,
    schema=SCHEMA,
    writer=writer,
    seed=42,
)

tables = workshop.tables
print(f"\n{workshop.brand_name}: created tables {tables}")
print(f"Vector Search endpoint for this run: {workshop.vs_endpoint_name}")
print(f"Chunk table for this run: {FULL_SCHEMA}.{workshop.chunk_table_name}")
print(f"Vector Search index for this run: {FULL_SCHEMA}.{workshop.doc_index_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Documents and Chunked Table
# MAGIC
# MAGIC Reads markdown from `verticals/<industry>/docs/` (retail/education: policies; financial_services: market-shock news), then chunks into an industry-appropriate table name.

# COMMAND ----------

from lib.chunking import build_chunk_table

chunk_dir = workshop.docs_dir
print(f"Source docs directory: {chunk_dir}")
chunk_table = build_chunk_table(chunk_dir, target_table=workshop.chunk_table_name)
writer.write_table(FULL_SCHEMA, chunk_table)

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Step 4: Create Vector Search Endpoint and Index
# MAGIC
# MAGIC Vector Search lets you find relevant policy documents using natural language instead of exact keyword matches.
# MAGIC This creates:
# MAGIC 1. A **Vector Search endpoint** (the compute that powers similarity search)
# MAGIC 2. A **Delta Sync index** on the policy docs table (automatically generates embeddings)
# MAGIC
# MAGIC The endpoint takes 5-10 minutes to become ready. The cell will wait automatically.

# COMMAND ----------

from lib.provisioning import ensure_vector_search_index

# Creates/reuses the endpoint, enables CDF on the chunk table, and (re)builds the
# Delta Sync index. Same shared code path the local CLI uses.
VS_ENDPOINT_NAME = workshop.vs_endpoint_name
VS_INDEX_NAME = ensure_vector_search_index(
    w,
    writer,
    endpoint_name=VS_ENDPOINT_NAME,
    full_schema=FULL_SCHEMA,
    chunk_table=workshop.chunk_table_name,
    index_name=workshop.doc_index_name,
    org_id=WORKSPACE_ORG_ID,
)

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Step 5: Create Genie Space
# MAGIC
# MAGIC Genie lets you ask questions about your data in plain English. It converts your questions into SQL automatically.
# MAGIC
# MAGIC This creates a Genie Space connected to all industry data tables.

# COMMAND ----------

from lib.provisioning import ensure_genie_space

GENIE_SPACE_TITLE = workshop.genie_title
genie_space_id = ensure_genie_space(
    w,
    title=GENIE_SPACE_TITLE,
    description=workshop.genie_description,
    table_identifiers=[f"{FULL_SCHEMA}.{t}" for t in tables],
    org_id=WORKSPACE_ORG_ID,
)

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Step 6: Create MLflow Experiment
# MAGIC
# MAGIC MLflow tracks your agent's performance. This creates an experiment where traces and evaluation metrics will be logged.

# COMMAND ----------

from lib.provisioning import ensure_mlflow_experiment

username = w.current_user.me().user_name
experiment_name, experiment_id = ensure_mlflow_experiment(
    suffix=workshop.mlflow_experiment_suffix,
    username=username,
    host=WORKSPACE_HOST,
)

# COMMAND ----------

from lib.provisioning import register_optional_udf

register_optional_udf(
    writer,
    udf_sql=workshop.optional_udf_sql,
    udf_name=workshop.optional_udf_name,
    full_schema=FULL_SCHEMA,
    host=WORKSPACE_HOST,
)

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Setup Complete
# MAGIC
# MAGIC All resources have been created. Here's a summary of everything that's ready for you:

# COMMAND ----------

from lib.workspace_links import (
    genie_space_url,
    mlflow_experiment_url,
    print_asset_link,
    uc_function_url,
    vector_search_endpoint_url,
    vector_search_index_catalog_url,
    vector_search_index_url_from_api,
)

print("=" * 70)
print(f"  {workshop.brand_name.upper()} WORKSHOP SETUP COMPLETE")
print("=" * 70)
print()
print(f"  Catalog/Schema:     {FULL_SCHEMA}")
print()
def _row_count(table_name: str) -> int:
    rows = writer.query(f"SELECT COUNT(*) FROM {FULL_SCHEMA}.{table_name}")
    return int(rows[0][0]) if rows and rows[0] else 0

print("  Data Tables:")
for table in tables:
    print(f"    {table:25s} {_row_count(table):>8,} rows")
chunks_count = _row_count(workshop.chunk_table_name)
print(f"    {workshop.chunk_table_name:25s} {chunks_count:>8,} chunks")
print()
print(f"  Vector Search Endpoint:  {VS_ENDPOINT_NAME}")
print(f"  Vector Search Index:     {VS_INDEX_NAME}")
print()
print("  Validation links:")
print_asset_link(
    "Vector Search endpoint",
    vector_search_endpoint_url(WORKSPACE_HOST, VS_ENDPOINT_NAME, WORKSPACE_ORG_ID),
)
_index_summary_url = vector_search_index_url_from_api(w, VS_INDEX_NAME)
if not _index_summary_url:
    _index_summary_url = vector_search_index_catalog_url(WORKSPACE_HOST, VS_INDEX_NAME)
print_asset_link("Vector Search index", _index_summary_url)
if genie_space_id:
    print(f"  Genie Space ID:          {genie_space_id}")
    print(f"  Genie Space Title:       {GENIE_SPACE_TITLE}")
    print_asset_link("Genie Space", genie_space_url(WORKSPACE_HOST, genie_space_id, WORKSPACE_ORG_ID))
print()
print(f"  MLflow Experiment:       {experiment_name}")
print(f"  MLflow Experiment ID:    {experiment_id}")
print_asset_link("MLflow experiment", mlflow_experiment_url(WORKSPACE_HOST, experiment_id))
if workshop.optional_udf_name:
    print_asset_link(
        "UC function",
        uc_function_url(WORKSPACE_HOST, FULL_SCHEMA, workshop.optional_udf_name),
    )
print()
print("=" * 70)
print("  Next Steps:")
print("    1. Open the Genie Space and try asking questions about your data")
print("    2. Explore the Vector Search index in Catalog Explorer")
print("    3. Open the Databricks Playground to build your first agent")
print("    4. See the README for detailed workshop modules")
print("=" * 70)

# COMMAND ----------

# import mlflow 
# mlflow.create_experiment(
#     name="/Users/<your email>/<experiment name>",
#     artifact_location="dbfs:/Volumes/<catalog>/<schema>/<volume>/mlflow-artifacts"
# )

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Playground Industry System Prompt
# MAGIC
# MAGIC Use this system prompt for the eventual agent in the playground.

# COMMAND ----------

from verticals.registry import get_system_prompt
system_prompt = get_system_prompt(INDUSTRY)


print("=" * 70)
print(f"  SYSTEM PROMPT: \n\n {system_prompt}")
print("=" * 70)

# COMMAND ----------


