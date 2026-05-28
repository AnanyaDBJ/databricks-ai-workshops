"""Meridian Capital Partners — financial services tables for workshop demo.

All workshop tables are written to {catalog}.{schema} from 01_quickstart_setup.py widgets.
The generator never writes to the provider's market_data schema.
"""

import json
import random
from datetime import datetime, timedelta

from lib.demo_names import CITIES_STATES, FIRST_NAMES, LAST_NAMES

# Databricks Marketplace: Sample Market Data - Daily Price Data (Delta Sharing)
# https://e2-demo-field-eng.cloud.databricks.com/marketplace/consumer/listings/0f7c65e3-875a-40e2-bd58-5c8bcadbdc2b
# Install into the Catalog widget; read once from {catalog}.market_data, land in {catalog}.{schema}.
SHARE_SCHEMA = "market_data"
DAILY_PRICE_TABLE = "dailyprice"
COMPANY_PROFILE_TABLE = "company_profile"

FIRST_PARTY_TABLES = ["clients", "accounts", "portfolio_holdings"]
MARKET_DATA_TABLES = [DAILY_PRICE_TABLE, COMPANY_PROFILE_TABLE]
TABLES = FIRST_PARTY_TABLES + MARKET_DATA_TABLES


def _phone():
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"


def _email(first, last):
    domain = random.choice(["meridiancapital.com", "investor.com", "familyoffice.com"])
    return f"{first.lower()}.{last.lower()}@{domain}"


def _fqn(catalog: str, schema: str, table: str) -> str:
    return f"{catalog}.{schema}.{table}"


def _share_fqn(catalog: str, table: str) -> str:
    return f"`{catalog}`.`{SHARE_SCHEMA}`.`{table}`"


def _resolve_catalog_schema(
    full_schema: str,
    catalog: str | None,
    schema: str | None,
) -> tuple[str, str]:
    if catalog and schema:
        return catalog, schema
    parts = full_schema.split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"full_schema must be catalog.schema, got '{full_schema}'")
    return parts[0], parts[1]


def _materialize_market_data_tables(spark, catalog: str, schema: str, share_catalog: str) -> None:
    """Snapshot share tables into the workshop schema (never write to market_data)."""
    for table in MARKET_DATA_TABLES:
        source = _share_fqn(share_catalog, table)
        target = _fqn(catalog, schema, table)
        spark.sql(f"CREATE OR REPLACE TABLE {target} AS SELECT * FROM {source}")
        count = spark.table(target).count()
        print(f"Created {target} — {count:,} rows (snapshot from Delta Share)")


def _symbols_from_workshop_schema(spark, catalog: str, schema: str, limit: int = 400) -> list[str]:
    daily = _fqn(catalog, schema, DAILY_PRICE_TABLE)
    rows = spark.sql(
        f"""
        SELECT ticker
        FROM (
          SELECT DISTINCT ticker
          FROM {daily}
          WHERE ticker IS NOT NULL AND ticker NOT IN ('NaN', 'nan', '')
        )
        ORDER BY ticker
        LIMIT {int(limit)}
        """
    ).collect()
    symbols = [r["ticker"] for r in rows]
    if not symbols:
        raise ValueError(
            f"No tickers in {daily}. "
            "Install the Marketplace listing into the Catalog widget, then re-run setup."
        )
    return symbols


def _save(spark, catalog: str, schema: str, table, rows):
    fqn = _fqn(catalog, schema, table)
    spark.createDataFrame(rows).write.mode("overwrite").saveAsTable(fqn)
    print(f"Created {fqn} — {len(rows)} rows")


def generate(
    spark,
    full_schema: str,
    seed: int = 42,
    catalog: str | None = None,
    schema: str | None = None,
    market_data_catalog: str | None = None,
) -> list[str]:
    catalog, schema = _resolve_catalog_schema(full_schema, catalog, schema)
    share_catalog = market_data_catalog or catalog
    random.seed(seed)

    # Land 3rd-party market data in the target schema first (read share, write workshop schema only).
    _materialize_market_data_tables(spark, catalog, schema, share_catalog)
    symbols = _symbols_from_workshop_schema(spark, catalog, schema)
    as_of_date = datetime.utcnow().strftime("%Y-%m-%d")

    clients = []
    for i in range(1, 101):
        first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        city, state = random.choice(CITIES_STATES)
        clients.append({
            "client_id": f"CLT-{i:04d}",
            "first_name": first,
            "last_name": last,
            "email": _email(first, last),
            "phone": _phone(),
            "city": city,
            "state": state,
            "country": "US" if len(state) == 2 else state,
            "kyc_tier": random.choices(["Standard", "Enhanced", "PEP"], weights=[70, 25, 5])[0],
            "risk_rating": random.choices(["Low", "Medium", "High"], weights=[50, 35, 15])[0],
            "onboard_date": (datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2200))).strftime("%Y-%m-%d"),
            "preferences": json.dumps({
                "asset_classes": random.sample(["Equity", "Fixed Income", "ETF"], k=random.randint(1, 2)),
                "esg_screen": random.choice([True, False]),
            }),
        })
    _save(spark, catalog, schema, "clients", clients)

    accounts = []
    for acc_id in range(1, 201):
        client = random.choice(clients)
        accounts.append({
            "account_id": f"ACC-{acc_id:05d}",
            "client_id": client["client_id"],
            "account_type": random.choice(["Brokerage", "Retirement", "Trust", "Institutional"]),
            "status": random.choices(["Active", "Restricted", "Closed"], weights=[90, 7, 3])[0],
            "open_date": (datetime(2019, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d"),
            "cash_balance_usd": round(random.uniform(5_000, 500_000), 2),
        })
    _save(spark, catalog, schema, "accounts", accounts)

    holdings = []
    holding_id = 1
    for account in accounts:
        if account["status"] == "Closed":
            continue
        for _ in range(random.randint(3, 12)):
            symbol = random.choice(symbols)
            qty = round(random.uniform(10, 5000), 2)
            cost_basis = round(random.uniform(15, 800), 4)
            holdings.append({
                "holding_id": f"HLD-{holding_id:06d}",
                "account_id": account["account_id"],
                "symbol": symbol,
                "quantity": qty,
                "cost_basis_usd": cost_basis,
                "as_of_date": as_of_date,
            })
            holding_id += 1
    _save(spark, catalog, schema, "portfolio_holdings", holdings)

    ws = f"{catalog}.{schema}"
    print(
        f"All tables in {ws}: {', '.join(TABLES)}\n"
        f"Example join:\n"
        f"  SELECT h.*, d.close, c.industry\n"
        f"  FROM {ws}.portfolio_holdings h\n"
        f"  JOIN {ws}.company_profile c ON h.symbol = c.ticker\n"
        f"  JOIN {ws}.dailyprice d ON h.symbol = d.ticker"
    )
    return TABLES
