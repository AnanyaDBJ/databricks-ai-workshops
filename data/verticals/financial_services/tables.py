"""Meridian Capital Partners — financial services tables for workshop demo."""

import json
import random
from datetime import datetime, timedelta

from lib.demo_names import CITIES_STATES, FIRST_NAMES, LAST_NAMES

TABLES = [
    "clients", "instruments", "branches", "accounts",
    "trades", "trade_legs", "settlements",
]

SYMBOLS = [
    ("AAPL", "Equity", 185.0), ("MSFT", "Equity", 420.0), ("GOOGL", "Equity", 175.0),
    ("JPM", "Equity", 195.0), ("BAC", "Equity", 38.0), ("NVDA", "Equity", 880.0),
    ("SPY", "ETF", 520.0), ("QQQ", "ETF", 445.0), ("TLT", "Bond ETF", 92.0),
    ("GLD", "Commodity ETF", 215.0), ("VZ", "Equity", 40.0), ("XOM", "Equity", 115.0),
]

BRANCH_NAMES = [
    "Meridian New York", "Meridian London", "Meridian Singapore",
    "Meridian Chicago", "Meridian San Francisco", "Meridian Zurich",
    "Meridian Hong Kong", "Meridian Boston", "Meridian Toronto", "Meridian Dubai",
]


def _phone():
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"


def _email(first, last):
    domain = random.choice(["meridiancapital.com", "investor.com", "familyoffice.com"])
    return f"{first.lower()}.{last.lower()}@{domain}"


def _save(spark, full_schema, table, rows):
    spark.createDataFrame(rows).write.mode("overwrite").saveAsTable(f"{full_schema}.{table}")
    print(f"Created {full_schema}.{table} — {len(rows)} rows")


def generate(spark, full_schema: str, seed: int = 42) -> list[str]:
    random.seed(seed)

    clients = []
    for i in range(1, 201):
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
                "asset_classes": random.sample(["Equity", "Fixed Income", "ETF", "Options"], k=random.randint(1, 3)),
                "esg_screen": random.choice([True, False]),
            }),
        })
    _save(spark, full_schema, "clients", clients)

    instruments = []
    for i, (sym, asset_class, base_price) in enumerate(SYMBOLS, 1):
        instruments.append({
            "instrument_id": f"INS-{i:03d}",
            "symbol": sym,
            "asset_class": asset_class,
            "exchange": random.choice(["NYSE", "NASDAQ", "LSE", "SGX"]),
            "currency": random.choice(["USD", "USD", "USD", "EUR", "GBP"]),
            "last_price": round(base_price * random.uniform(0.95, 1.05), 4),
        })
    while len(instruments) < 300:
        base = random.choice(SYMBOLS)
        instruments.append({
            "instrument_id": f"INS-{len(instruments) + 1:03d}",
            "symbol": f"{base[0]}{random.randint(1, 9)}",
            "asset_class": base[1],
            "exchange": "NASDAQ",
            "currency": "USD",
            "last_price": round(base[2] * random.uniform(0.8, 1.2), 4),
        })
    _save(spark, full_schema, "instruments", instruments)

    branches = []
    for i, name in enumerate(BRANCH_NAMES, 1):
        city, state = CITIES_STATES[i % len(CITIES_STATES)]
        branches.append({
            "branch_id": f"BR-{i:02d}",
            "name": name,
            "city": city,
            "region": state,
            "desk_type": random.choice(["Wealth", "Institutional", "Trading", "Prime"]),
            "phone": _phone(),
        })
    _save(spark, full_schema, "branches", branches)

    accounts = []
    for acc_id in range(1, 401):
        client, branch = random.choice(clients), random.choice(branches)
        accounts.append({
            "account_id": f"ACC-{acc_id:05d}",
            "client_id": client["client_id"],
            "branch_id": branch["branch_id"],
            "account_type": random.choice(["Brokerage", "Margin", "Retirement", "Institutional", "Trust"]),
            "status": random.choices(["Active", "Restricted", "Closed"], weights=[88, 7, 5])[0],
            "margin_enabled": random.choice([True, False]),
            "open_date": (datetime(2019, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d"),
            "balance_usd": round(random.uniform(10_000, 5_000_000), 2),
        })
    _save(spark, full_schema, "accounts", accounts)

    trades, trade_legs = [], []
    leg_id = 1
    for trade_id in range(1, 2001):
        account, instrument = random.choice(accounts), random.choice(instruments)
        qty = random.randint(10, 5000)
        price = instrument["last_price"]
        trade_value = round(qty * price, 2)
        trade_dt = datetime(2024, 1, 2, 9, 30) + timedelta(
            days=random.randint(0, 300), hours=random.randint(0, 6), minutes=random.randint(0, 59)
        )
        trades.append({
            "trade_id": f"TRD-{trade_id:06d}",
            "account_id": account["account_id"],
            "instrument_id": instrument["instrument_id"],
            "symbol": instrument["symbol"],
            "side": random.choice(["BUY", "SELL"]),
            "order_type": random.choice(["Market", "Limit", "Stop", "Stop-Limit"]),
            "quantity": float(qty),
            "price": price,
            "trade_value": trade_value,
            "commission": round(max(0.99, trade_value * 0.001), 2),
            "trade_timestamp": trade_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "status": random.choices(["Filled", "Partial", "Cancelled", "Rejected"], weights=[92, 3, 3, 2])[0],
        })
        for _ in range(random.randint(1, 3)):
            trade_legs.append({
                "leg_id": f"LEG-{leg_id:07d}",
                "trade_id": f"TRD-{trade_id:06d}",
                "allocation_pct": round(100 / 3, 2),
                "quantity": float(max(1, qty // 3)),
                "venue": random.choice(["NYSE", "NASDAQ", "BATS", "IEX"]),
                "execution_price": round(price * random.uniform(0.999, 1.001), 4),
            })
            leg_id += 1
    _save(spark, full_schema, "trades", trades)
    _save(spark, full_schema, "trade_legs", trade_legs)

    settlements = []
    for sett_id in range(1, 401):
        trade = random.choice(trades)
        settlements.append({
            "settlement_id": f"SET-{sett_id:05d}",
            "trade_id": trade["trade_id"],
            "account_id": trade["account_id"],
            "settlement_type": random.choice(
                ["Trade Settlement", "Dividend", "Fee", "Wire In", "Wire Out", "Interest"]
            ),
            "amount_usd": round(random.uniform(-500_000, 500_000), 2),
            "settlement_date": (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 300))).strftime("%Y-%m-%d"),
            "status": random.choices(["Settled", "Pending", "Failed"], weights=[85, 12, 3])[0],
        })
    _save(spark, full_schema, "settlements", settlements)
    return TABLES
