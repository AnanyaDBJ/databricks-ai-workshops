# Data Setup

> **This is the first step for all workshop levels.** Complete this setup before starting any workshop (Simple, Medium, or Advanced).

This creates the shared dataset that all workshop levels depend on: retail data tables, chunked policy documents, a Vector Search index, a Genie Space, and an MLflow experiment.

---

## Choose Your Path

| Path | Best for | Time |
|------|----------|------|
| **[Path A: Local CLI](#path-a-local-cli)** | Local development, running the advanced workshop locally | ~15 min |
| **[Path B: Workspace Notebook](#path-b-workspace-notebook)** | Everything inside Databricks, no local tools needed | ~15 min |

Both paths produce the exact same result. Pick one.

---

## Path A: Local CLI

Run these scripts from your local machine. They connect to your Databricks workspace via the CLI.

### Prerequisites

| Tool | Install |
|------|---------|
| Databricks CLI | `brew tap databricks/tap && brew install databricks` |
| Python 3.9+ | [python.org](https://www.python.org/downloads/) |
| jq | `brew install jq` |

You also need:
- A **running SQL warehouse** (Compute > SQL Warehouses in Databricks)
- **Unity Catalog** access (permission to create tables)

### Step 1: Authenticate

```bash
databricks auth login --profile DEFAULT
```

Follow the browser prompts. Verify it worked:

```bash
databricks current-user me --profile DEFAULT
```

### Step 2: Find your warehouse ID

```bash
databricks warehouses list --profile DEFAULT --output json | jq -r '.[] | "\(.id)  \(.name)  \(.state)"'
```

Pick a warehouse that shows `RUNNING`. Copy its ID.

### Step 3: Create catalog and schema

Run in the Databricks SQL Editor, or via CLI:

```bash
databricks api post /api/2.0/sql/statements \
  --profile DEFAULT \
  --json '{
    "warehouse_id": "<WAREHOUSE-ID>",
    "statement": "CREATE CATALOG IF NOT EXISTS <CATALOG>; CREATE SCHEMA IF NOT EXISTS <CATALOG>.<SCHEMA>;"
  }'
```

Replace `<CATALOG>` and `<SCHEMA>` with your chosen names (e.g., `my_catalog` and `retail_agent`).

### Step 4: Generate retail data tables

From the repository root:

```bash
python data/local_cli_setup_script/execute_sql.py \
  --profile DEFAULT \
  --warehouse-id <WAREHOUSE-ID> \
  --catalog <CATALOG> \
  --schema <SCHEMA>
```

This creates 6 tables: `customers`, `products`, `stores`, `transactions`, `transaction_items`, `payment_history`.

### Step 5: Generate policy document chunks

```bash
python data/local_cli_setup_script/execute_chunking.py \
  --profile DEFAULT \
  --warehouse-id <WAREHOUSE-ID> \
  --catalog <CATALOG> \
  --schema <SCHEMA>
```

This chunks 7 policy documents into the `policy_docs_chunked` table for Vector Search.

### Step 6: Create Vector Search index + Genie Space

```bash
python data/local_cli_setup_script/create_resources.py \
  --profile DEFAULT \
  --warehouse-id <WAREHOUSE-ID> \
  --catalog <CATALOG> \
  --schema <SCHEMA>
```

This takes 5-10 minutes (Vector Search endpoint provisioning). When done, it prints:

```
============================================================
SUMMARY
============================================================
  Vector Search Endpoint: <endpoint-name>
  Vector Search Index:    <CATALOG>.<SCHEMA>.policy_docs_index
  Genie Space ID:         01ef...abcd

Add these to your advanced/.env file:
  VECTOR_SEARCH_INDEX=<CATALOG>.<SCHEMA>.policy_docs_index
  GENIE_SPACE_ID=01ef...abcd
```

**Save these values** — you'll need them in your workshop level's configuration step.

### Done!

You now have everything ready. Go to your workshop level:

| Level | Next step |
|-------|-----------|
| Simple (L100) | [`simple/LAB_GUIDE.md`](../simple/LAB_GUIDE.md) |
| Medium (L200) | [`medium/lab_instructions/SETUP_GUIDE_WORKSPACE_ONLY.md`](../medium/lab_instructions/SETUP_GUIDE_WORKSPACE_ONLY.md) |
| Advanced (L300) — Local | [`advanced/WORKSHOP_INSTRUCTIONS.md`](../advanced/WORKSHOP_INSTRUCTIONS.md) |
| Advanced (L300) — Workspace | [`advanced/WORKSHOP_INSTRUCTIONS_WORKSPACE.md`](../advanced/WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |

---

## Path B: Workspace Notebook

Run everything inside Databricks — no local tools needed.

### Prerequisites

- A Databricks workspace with **Unity Catalog**, **Vector Search**, and **Foundation Model API** enabled
- A **running SQL warehouse** (Compute > SQL Warehouses)
- The repository imported as a Git Folder (Workspace > Repos > Add > Git Folder)

### Step 1: Open the notebook

Navigate to `data/workspace_setup_script/01_quickstart_setup.py` in the workspace file browser and open it.

### Step 2: Configure and run

1. At the top, select your **catalog** and **schema** from the dropdown widgets
2. Click **Run All**
3. Wait ~10-15 minutes (most time is Vector Search endpoint provisioning)

### Step 3: Copy the output values

When complete, the notebook prints a summary:

```
======================================================================
  WORKSHOP SETUP COMPLETE
======================================================================
  Catalog/Schema:        my_catalog.retail_agent

  Vector Search Index:   my_catalog.retail_agent.policy_docs_index
  Genie Space ID:        01ef...abcd
  MLflow Experiment ID:  1234567890123456
======================================================================
```

**Save these values** — you'll need them in your workshop level's configuration step.

### Done!

You now have everything ready. Go to your workshop level:

| Level | Next step |
|-------|-----------|
| Simple (L100) | [`simple/LAB_GUIDE.md`](../simple/LAB_GUIDE.md) |
| Medium (L200) | [`medium/lab_instructions/SETUP_GUIDE_WORKSPACE_ONLY.md`](../medium/lab_instructions/SETUP_GUIDE_WORKSPACE_ONLY.md) |
| Advanced (L300) — Workspace | [`advanced/WORKSHOP_INSTRUCTIONS_WORKSPACE.md`](../advanced/WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |

---

## What You Now Have

| Resource | Description |
|----------|-------------|
| `customers` table | 200 synthetic customers |
| `products` table | ~500 retail products |
| `stores` table | 10 store locations |
| `transactions` table | 2,000 transactions |
| `transaction_items` table | ~8,000 line items |
| `payment_history` table | 400 payment records |
| `policy_docs_chunked` table | Policy documents split into searchable chunks |
| Vector Search index | Semantic search over policy documents |
| Genie Space | Natural language querying of retail data |
| MLflow Experiment | Agent tracing and evaluation |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `JSONDecodeError` or auth errors | Auth expired — run `databricks auth login --profile DEFAULT` |
| `create_resources.py` times out | VS endpoint can take 10+ min — re-run, it's idempotent |
| Vector Search index shows "Syncing" | Normal — wait 5-10 min after creation for initial sync |
| Notebook widget doesn't show catalogs | Ensure your cluster has Unity Catalog access |
| `WAREHOUSE_NOT_FOUND` | Start a SQL warehouse first (Compute > SQL Warehouses) |

---

## Technical Reference

### Folder structure

```
data/
├── README.md                              ← you are here
├── policy_docs/                           # Source markdown policy documents (7 files)
│   ├── customer_service_guidelines.md
│   ├── delivery_pickup_procedures.md
│   ├── membership_loyalty_program.md
│   ├── privacy_policy.md
│   ├── product_safety_recalls.md
│   ├── return_refund_policy.md
│   └── store_operating_procedures.md
├── local_cli_setup_script/                # Scripts that run from your local machine
│   ├── execute_sql.py                     # Generate structured tables via SQL REST API
│   ├── execute_chunking.py                # Chunk policy docs via SQL REST API
│   └── create_resources.py                # Create Vector Search + Genie Space
└── workspace_setup_script/                # Databricks notebook (does everything on-cluster)
    └── 01_quickstart_setup.py
```

### Script arguments

All local CLI scripts accept the same arguments:

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--warehouse-id` | Yes | — | SQL warehouse ID |
| `--catalog` | Yes | — | Unity Catalog name |
| `--schema` | Yes | — | Schema name |
| `--profile` | No | `DEFAULT` | Databricks CLI profile |

`create_resources.py` also accepts:
| Argument | Default | Description |
|----------|---------|-------------|
| `--vs-endpoint-name` | auto-generated | Vector Search endpoint name |
| `--vs-index-name` | `policy_docs_index` | Vector Search index name |

### Notes

- All scripts use `random.seed(42)` for reproducibility
- `create_resources.py` is idempotent — safe to re-run if interrupted
- Scripts can be run from any directory (paths resolve relative to the script file)
