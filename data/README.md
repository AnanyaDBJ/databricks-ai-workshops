# Synthetic Data Generation for Workshop

This folder contains scripts and source documents to generate all the data required for the QSIC workshop. It produces two types of data in Unity Catalog:

1. **Structured retail data** — synthetic customers, products, stores, transactions, and payments
2. **Chunked policy documents** — markdown policy docs split into overlapping text chunks for vector search

## Folder Structure

```
data/
├── README.md
├── create_structured_data.py     # PySpark script — generates structured tables (run on cluster or locally)
├── create_chunked_docs.py        # PySpark script — chunks policy docs (requires UC Volumes access)
├── execute_sql.py                # Local script — generates structured tables via SQL REST API
├── execute_chunking.py           # Local script — chunks policy docs via SQL REST API
├── run_sql_generation.py         # Local script — generates structured tables via Databricks CLI
└── policy_docs/                  # Source markdown policy documents (7 files)
    ├── customer_service_guidelines.md
    ├── delivery_pickup_procedures.md
    ├── membership_loyalty_program.md
    ├── privacy_policy.md
    ├── product_safety_recalls.md
    ├── return_refund_policy.md
    └── store_operating_procedures.md
```

## Scripts Overview

There are **two tasks**, each with multiple execution variants:

### Task 1: Generate Structured Retail Data

Creates 6 tables: `customers` (200 rows), `products` (~500), `stores` (10), `transactions` (2000), `transaction_items` (~8000+), `payment_history` (400).

| Script | Runs On | Method |
|--------|---------|--------|
| `create_structured_data.py` | Databricks cluster or local with PySpark | PySpark DataFrames |
| `execute_sql.py` | Local machine | SQL via REST API (`urllib`) |
| `run_sql_generation.py` | Local machine | SQL via `databricks api` CLI |

### Task 2: Chunk Policy Documents for Vector Search

Reads the 7 markdown files from `policy_docs/`, splits them into overlapping chunks (1000 chars, 200 overlap), and writes to a `policy_docs_chunked` table.

| Script | Runs On | Method |
|--------|---------|--------|
| `create_chunked_docs.py` | Databricks cluster or local with PySpark | PySpark + UC Volumes |
| `execute_chunking.py` | Local machine | SQL via REST API (`urllib`) |

## TODO: What to Change for a New Workspace

### Required Changes (all 5 scripts)

Update these two constants at the top of **every** script:

| Constant | Current Value | Update To |
|----------|---------------|-----------|
| `CATALOG` | `"ananyaroy"` | Your Unity Catalog name |
| `SCHEMA` | `"retail_wiab"` | Your target schema name |

Files to update:
- [ ] `create_structured_data.py` — lines with `CATALOG` and `SCHEMA`
- [ ] `create_chunked_docs.py` — lines with `CATALOG` and `SCHEMA`
- [ ] `execute_sql.py` — lines with `CATALOG` and `SCHEMA`
- [ ] `execute_chunking.py` — lines with `CATALOG` and `SCHEMA`
- [ ] `run_sql_generation.py` — lines with `CATALOG` and `SCHEMA`

### Prerequisites for the New Workspace

- [ ] Create the target catalog and schema in Unity Catalog
- [ ] For PySpark scripts: run on a Databricks cluster (e.g. via `databricks jobs submit`) or locally with PySpark + UC connectivity
- [ ] For `create_chunked_docs.py`: create a UC Volume and upload `policy_docs/*.md` files:
  ```bash
  databricks fs cp ./policy_docs/ dbfs:/Volumes/<CATALOG>/<SCHEMA>/policy_docs/ --recursive --profile <profile>
  ```
- [ ] For local scripts: ensure the `databricks` CLI is installed and configured with a profile
- [ ] For local scripts: have a SQL warehouse running and note its warehouse ID

### Runtime Arguments (local scripts only)

The local scripts accept CLI arguments — no hardcoded workspace URLs:

```bash
# Structured data generation
python execute_sql.py --profile <PROFILE> --warehouse-id <WAREHOUSE_ID>
python run_sql_generation.py --profile <PROFILE> --warehouse-id <WAREHOUSE_ID>

# Document chunking
python execute_chunking.py --profile <PROFILE> --warehouse-id <WAREHOUSE_ID>
```

### Other Considerations

- [ ] Verify the Databricks CLI profile points to the correct workspace host
- [ ] Ensure the service principal or user has `CREATE TABLE` and `WRITE` permissions on the target schema
- [ ] If changing the chunking parameters (size/overlap), update both `create_chunked_docs.py` and `execute_chunking.py` to keep them in sync
- [ ] All scripts use `random.seed(42)` for reproducibility — data will be identical across runs
