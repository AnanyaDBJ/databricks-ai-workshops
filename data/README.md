# Workshop synthetic data

Pick an **industry** in [`01_quickstart_setup.py`](01_quickstart_setup.py) (widget: `retail`, `education`, or `financial_services`). The notebook generates tables and chunks markdown from each vertical’s `docs/` folder.

## Layout

```
data/
├── 00-utils.ipynb              # optional: MLflow artifacts on UC Volume (restricted networks)
├── 01_quickstart_setup.py      # main workshop setup notebook
├── lib/
│   ├── generate.py
│   ├── chunking.py             # writes policy_docs_chunked (UC table name unchanged)
│   └── demo_names.py
├── verticals/
│   ├── retail/
│   │   ├── tables.py
│   │   └── docs/               # source markdown for Vector Search
│   ├── education/
│   │   ├── tables.py
│   │   └── docs/
│   └── financial_services/
│       ├── tables.py
│       └── docs/
└── scripts/
    └── generate_structured_data.py
```

## Industries

| Industry | Brand | Tables | Docs |
|----------|-------|--------|------|
| `education` (default) | EduPath Academy | 6 retail-shaped table names, school semantics | `verticals/education/docs/` |
| `retail` | FreshMart | Same 6 tables, grocery semantics | `verticals/retail/docs/` |
| `financial_services` | Meridian Capital Partners | `clients`, `instruments`, `branches`, `accounts`, `trades`, `trade_legs`, `settlements` | `verticals/financial_services/docs/` |

## Local CLI (optional)

```bash
cd data
python scripts/generate_structured_data.py --industry retail --catalog CATALOG --schema SCHEMA
python local_cli_setup_script/execute_chunking.py --profile PROFILE --warehouse-id ID
```

`execute_chunking.py` chunks **retail** docs only.

## Note on financial_services

Agents and lab guides written for education/retail still expect the 6-table names. Use `financial_services` when you want financial-native tables and update Genie/agent prompts accordingly.
