# Workshop synthetic data

Pick an **industry** in [`01_quickstart_setup.py`](01_quickstart_setup.py) (widget: `retail`, `education`, or `financial_services`). The notebook generates tables and chunks markdown from each vertical’s `docs/` folder.

## Layout

```
data/
├── 00-utils.ipynb              # optional: MLflow artifacts on UC Volume (restricted networks)
├── 01_quickstart_setup.py      # main workshop setup notebook
├── lib/
│   ├── generate.py             # dispatches to verticals/registry.py
│   ├── chunking.py             # writes policy_docs_chunked (UC table name unchanged)
│   └── demo_names.py
├── verticals/
│   ├── registry.py             # lists onboarded industries
│   ├── retail/
│   │   ├── workshop.py         # brand, Genie/VS names, optional UC function
│   │   ├── tables.py
│   │   └── docs/               # source markdown for Vector Search
│   ├── education/
│   │   ├── workshop.py
│   │   ├── tables.py
│   │   └── docs/
│   └── financial_services/
│       ├── workshop.py
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
| `financial_services` | Meridian Capital Partners | `{catalog}.{schema}`: clients, accounts, portfolio_holdings, dailyprice, company_profile | `verticals/financial_services/docs/` |

## Local CLI (optional)

```bash
cd data
python scripts/generate_structured_data.py --industry retail --catalog CATALOG --schema SCHEMA
python local_cli_setup_script/execute_chunking.py --profile PROFILE --warehouse-id ID
```

`execute_chunking.py` chunks **retail** docs only.

## Financial services and Marketplace market data

For `financial_services`, **all workshop tables** (including market data) live in `{catalog}.{schema}` from the setup widgets. The generator does **not** write to the provider `market_data` schema.

Install the [Sample Market Data - Daily Price Data](https://e2-demo-field-eng.cloud.databricks.com/marketplace/consumer/listings/0f7c65e3-875a-40e2-bd58-5c8bcadbdc2b) listing into the **Catalog** widget name (creates read-only `{catalog}.market_data.*`). Setup snapshots `dailyprice` and `company_profile` into `{catalog}.{schema}` once; use the **Schema** widget for your workshop schema (not `market_data`).

Other verticals (`education`, `retail`) use fully synthetic data in `{catalog}.{schema}` only.

Agents and lab guides written for education/retail still expect the 6-table names. Use `financial_services` when you want portfolio + market-data joins and update Genie/agent prompts accordingly.

## Onboarding a new industry

1. Add `verticals/<industry>/` with `tables.py`, `docs/`, and `workshop.py` (see an existing vertical).
2. Register it in `verticals/registry.py` (`_REGISTRY` and import).
3. Add the industry id to the **Industry** widget in `01_quickstart_setup.py`.
4. If the vertical needs external data (like financial services Marketplace share), document setup in `workshop.py` and extend `01_quickstart_setup.py` only for vertical-specific prerequisites.

UC functions live in each vertical’s `workshop.py` (`udf_sql` / `udf_name`), not in `lib/generate.py`.
