"""Meridian Capital Partners — financial services tables for workshop demo.

All workshop tables are written to {catalog}.{schema} from the setup entrypoints.

Real market data (daily prices and company profiles for 29 tickers, 1999-2023)
ships with the repo as CSVs in the market_data/ folder — a one-time export of
the Databricks Marketplace "Sample Market Data - Daily Price Data" listing — so
setup needs no Delta Sharing or Marketplace access.

First-party data is driven by that real market data: a simulated BUY/SELL trade
ledger is generated per account on real trading dates at real closing prices,
and portfolio holdings, P&L, and cash balances are all derived from that
ledger — so every number reconciles with `trades` and `dailyprice`.

This module is Spark-free: it parses the bundled CSVs and computes the price
history / shock analysis in pure Python, returning ``TableData`` objects that
either writer (Spark on a cluster, or SQL REST API from a laptop) can persist.
"""

import csv
import gzip
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from lib.demo_names import CITIES_STATES, FIRST_NAMES, LAST_NAMES
from verticals.base import BundledCsvTable, TableData

MARKET_DATA_DIR = Path(__file__).parent / "market_data"
DAILY_PRICE_TABLE = "dailyprice"
COMPANY_PROFILE_TABLE = "company_profile"

FIRST_PARTY_TABLES = ["clients", "accounts", "trades", "portfolio_holdings"]
MARKET_DATA_TABLES = [DAILY_PRICE_TABLE, COMPANY_PROFILE_TABLE]
TABLES = FIRST_PARTY_TABLES + MARKET_DATA_TABLES
TABLE_DESCRIPTIONS = {
    "clients": "Client master records with KYC tier, risk rating, and profile attributes.",
    "accounts": "Investment account records tied to clients. Cash balance is derived from initial funding and the trades ledger.",
    "trades": "Simulated BUY/SELL trade ledger per account, executed on real trading dates at real closing prices (small slippage). Source of truth for holdings and P&L.",
    "portfolio_holdings": "Position-level holdings derived from the trades ledger: quantity, average cost basis, realized P&L, and mark-to-market value at the latest close.",
    "dailyprice": "Daily market pricing history for tradable symbols (real sample data bundled with the workshop).",
    "company_profile": "Reference company attributes and sector/industry metadata for tradable symbols.",
}

COLUMNS = {
    "clients": [
        ("client_id", "STRING"), ("first_name", "STRING"), ("last_name", "STRING"),
        ("email", "STRING"), ("phone", "STRING"), ("city", "STRING"), ("state", "STRING"),
        ("country", "STRING"), ("kyc_tier", "STRING"), ("risk_rating", "STRING"),
        ("onboard_date", "STRING"), ("preferences", "STRING"),
    ],
    "accounts": [
        ("account_id", "STRING"), ("client_id", "STRING"), ("account_type", "STRING"),
        ("status", "STRING"), ("open_date", "STRING"),
        ("initial_funding_usd", "DOUBLE"), ("cash_balance_usd", "DOUBLE"),
    ],
    "trades": [
        ("trade_id", "STRING"), ("account_id", "STRING"), ("symbol", "STRING"),
        ("side", "STRING"), ("trade_date", "STRING"), ("quantity", "INT"),
        ("execution_price_usd", "DOUBLE"), ("notional_usd", "DOUBLE"),
    ],
    "portfolio_holdings": [
        ("holding_id", "STRING"), ("account_id", "STRING"), ("symbol", "STRING"),
        ("quantity", "INT"), ("avg_cost_basis_usd", "DOUBLE"), ("realized_pnl_usd", "DOUBLE"),
        ("market_value_usd", "DOUBLE"), ("unrealized_pnl_usd", "DOUBLE"), ("as_of_date", "STRING"),
    ],
    "dailyprice": [
        ("date", "DATE"), ("open", "DOUBLE"), ("high", "DOUBLE"), ("low", "DOUBLE"),
        ("close", "DOUBLE"), ("adjClose", "DOUBLE"), ("vol", "DOUBLE"),
        ("divAmount", "DOUBLE"), ("splitFactor", "DOUBLE"), ("ticker", "STRING"),
    ],
    "company_profile": [
        ("country", "STRING"), ("currency", "STRING"), ("estimateCurrency", "STRING"),
        ("exchange", "STRING"), ("industry", "STRING"), ("ipo", "DATE"), ("logo", "STRING"),
        ("marketCap", "DOUBLE"), ("companyName", "STRING"), ("phone", "STRING"),
        ("sharesOutstanding", "DOUBLE"), ("ticker", "STRING"), ("website", "STRING"),
    ],
}

# Tickers the market-news documents cover — always part of the tradable universe
NEWS_TICKERS = ["AAPL", "TSLA"]
UNIVERSE_SIZE = 40
MIN_HISTORY_DAYS = 250
SHOCK_RETURN_THRESHOLD = -0.04  # single-day return at or below this is a "shock"


def _phone():
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"


def _email(first, last):
    domain = random.choice(["meridiancapital.com", "investor.com", "familyoffice.com"])
    return f"{first.lower()}.{last.lower()}@{domain}"


# How the CSV export renders NULL/NaN values
_CSV_NULLS = {"", "null", "NaN", "nan"}


def _to_date(value: str):
    return None if value in _CSV_NULLS else datetime.strptime(value, "%Y-%m-%d").date()


def _to_float(value: str):
    return None if value in _CSV_NULLS else float(value)


def _to_str(value: str):
    return None if value in _CSV_NULLS else value


def _read_csv_rows(path: Path) -> list[list[str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # header
        return list(reader)


def _parse_daily_rows() -> list[dict]:
    """Parse the bundled dailyprice CSV into typed dict rows (full history)."""
    path = MARKET_DATA_DIR / "dailyprice.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Bundled market data file missing: {path}. "
            "It ships with the repo under data/verticals/financial_services/market_data/."
        )
    names = [c for c, _ in COLUMNS["dailyprice"]]
    rows = []
    for r in _read_csv_rows(path):
        values = [_to_date(r[0]), *(_to_float(v) for v in r[1:9]), _to_str(r[9])]
        rows.append(dict(zip(names, values)))
    return rows


def _parse_profile_rows() -> list[dict]:
    """Parse the bundled company_profile CSV into typed dict rows."""
    path = MARKET_DATA_DIR / "company_profile.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Bundled market data file missing: {path}. "
            "It ships with the repo under data/verticals/financial_services/market_data/."
        )
    names = [c for c, _ in COLUMNS["company_profile"]]
    rows = []
    for r in _read_csv_rows(path):
        values = [
            _to_str(r[0]), _to_str(r[1]), _to_str(r[2]), _to_str(r[3]), _to_str(r[4]),
            _to_date(r[5]), _to_str(r[6]), _to_float(r[7]), _to_str(r[8]), _to_str(r[9]),
            _to_float(r[10]), _to_str(r[11]), _to_str(r[12]),
        ]
        rows.append(dict(zip(names, values)))
    return rows


def _price_history(daily_rows: list[dict]) -> dict[str, list[tuple[str, float]]]:
    """Build (date_str, close) series per ticker from parsed dailyprice rows.

    Mirrors the previous Spark query: keep tickers with a valid name, a positive
    close, and at least MIN_HISTORY_DAYS of history; limit to the most-traded
    UNIVERSE_SIZE tickers (always including NEWS_TICKERS).
    """
    series: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in daily_rows:
        ticker = row["ticker"]
        close = row["close"]
        date = row["date"]
        if not ticker or ticker in ("NaN", "nan", ""):
            continue
        if close is None or close <= 0 or date is None:
            continue
        series[ticker].append((date.isoformat(), close))

    counts = {t: len(s) for t, s in series.items() if len(s) >= MIN_HISTORY_DAYS}
    if not counts:
        raise ValueError(
            "No tickers with enough history in the bundled dailyprice CSV. "
            "The file at data/verticals/financial_services/market_data/dailyprice.csv "
            "may be missing or corrupt — re-sync the repo and re-run setup."
        )
    symbols = sorted(counts, key=lambda t: (-counts[t], t))
    universe = [t for t in NEWS_TICKERS if t in symbols]
    universe += [t for t in symbols if t not in universe][: UNIVERSE_SIZE - len(universe)]

    prices: dict[str, list[tuple[str, float]]] = {}
    for ticker in universe:
        prices[ticker] = sorted(series[ticker], key=lambda x: x[0])
    return prices


def _shock_days(prices: dict[str, list[tuple[str, float]]]) -> dict[str, set[str]]:
    """Dates where a ticker's close fell SHOCK_RETURN_THRESHOLD or more vs the prior close."""
    shocks: dict[str, set[str]] = {}
    for ticker, series in prices.items():
        days = set()
        for (_, prev_close), (date, close) in zip(series, series[1:]):
            if prev_close > 0 and (close / prev_close - 1) <= SHOCK_RETURN_THRESHOLD:
                days.add(date)
        shocks[ticker] = days
    return shocks


def _close_lookup(prices: dict[str, list[tuple[str, float]]]) -> dict[str, dict[str, float]]:
    return {t: dict(series) for t, series in prices.items()}


def _next_trading_date(series: list[tuple[str, float]], date: str) -> str | None:
    """First trading date in the series strictly after `date`."""
    for d, _ in series:
        if d > date:
            return d
    return None


class _Position:
    """Average-cost position bookkeeping for one account+symbol."""

    __slots__ = ("quantity", "avg_cost", "realized_pnl")

    def __init__(self):
        self.quantity = 0
        self.avg_cost = 0.0
        self.realized_pnl = 0.0

    def buy(self, qty: int, price: float):
        total_cost = self.avg_cost * self.quantity + price * qty
        self.quantity += qty
        self.avg_cost = total_cost / self.quantity

    def sell(self, qty: int, price: float):
        qty = min(qty, self.quantity)
        self.realized_pnl += (price - self.avg_cost) * qty
        self.quantity -= qty
        return qty


def _simulate_account_trades(
    account: dict,
    risk_rating: str,
    basket: list[str],
    prices: dict[str, list[tuple[str, float]]],
    shocks: dict[str, set[str]],
    rng: random.Random,
) -> tuple[list[dict], dict[str, _Position], float]:
    """Simulate one account's trade history.

    Returns (trade rows without trade_id, positions by symbol, final cash).
    Buys are capped by available cash; sells are capped by the held position.
    """
    cash = account["initial_funding_usd"]
    positions: dict[str, _Position] = {s: _Position() for s in basket}
    events: list[tuple[str, str, str]] = []  # (date, symbol, side_hint)

    # Initial buys shortly after the account opens
    for symbol in basket:
        start = _next_trading_date(prices[symbol], account["open_date"])
        if start:
            events.append((start, symbol, "BUY"))

    # Ongoing discretionary trades on random real trading dates
    n_trades = rng.randint(4, 10) if account["status"] == "Restricted" else rng.randint(10, 36)
    for _ in range(n_trades):
        symbol = rng.choice(basket)
        eligible = [d for d, _ in prices[symbol] if d > account["open_date"]]
        if eligible:
            events.append((rng.choice(eligible), symbol, "ANY"))

    # Reaction trades around shock days: risk-averse clients sell, risk-seekers buy the dip
    for symbol in basket:
        for shock_date in shocks.get(symbol, ()):
            if shock_date <= account["open_date"]:
                continue
            reaction = _next_trading_date(prices[symbol], shock_date)
            if not reaction:
                continue
            if risk_rating == "Low" and rng.random() < 0.5:
                events.append((reaction, symbol, "SELL"))
            elif risk_rating == "High" and rng.random() < 0.4:
                events.append((reaction, symbol, "BUY"))
            elif risk_rating == "Medium" and rng.random() < 0.15:
                events.append((reaction, symbol, rng.choice(["BUY", "SELL"])))

    closes = _close_lookup(prices)
    trades = []
    for date, symbol, side_hint in sorted(events):
        close = closes[symbol].get(date)
        if not close:
            continue
        position = positions[symbol]
        side = side_hint
        if side == "ANY":
            side = "SELL" if position.quantity > 0 and rng.random() < 0.4 else "BUY"

        price = round(close * (1 + rng.gauss(0, 0.003)), 4)
        if side == "BUY":
            budget = cash * rng.uniform(0.03, 0.12)
            qty = int(budget / price)
            if qty < 1 or qty * price > cash:
                continue
            position.buy(qty, price)
            cash -= qty * price
        else:
            if position.quantity < 1:
                continue
            qty = max(1, int(position.quantity * rng.uniform(0.2, 1.0)))
            qty = position.sell(qty, price)
            if qty < 1:
                continue
            cash += qty * price

        trades.append({
            "account_id": account["account_id"],
            "symbol": symbol,
            "side": side,
            "trade_date": date,
            "quantity": qty,
            "execution_price_usd": price,
            "notional_usd": round(qty * price, 2),
        })
    return trades, positions, cash


def _derive_holdings(
    positions_by_account: dict[str, dict[str, _Position]],
    latest_closes: dict[str, tuple[str, float]],
) -> list[dict]:
    """Mark open positions to market at the latest snapshot close."""
    holdings = []
    holding_id = 1
    for account_id, positions in positions_by_account.items():
        for symbol, pos in sorted(positions.items()):
            if pos.quantity < 1:
                continue
            as_of_date, close = latest_closes[symbol]
            holdings.append({
                "holding_id": f"HLD-{holding_id:06d}",
                "account_id": account_id,
                "symbol": symbol,
                "quantity": pos.quantity,
                "avg_cost_basis_usd": round(pos.avg_cost, 4),
                "realized_pnl_usd": round(pos.realized_pnl, 2),
                "market_value_usd": round(pos.quantity * close, 2),
                "unrealized_pnl_usd": round((close - pos.avg_cost) * pos.quantity, 2),
                "as_of_date": as_of_date,
            })
            holding_id += 1
    return holdings


def generate(seed: int = 42, **_ignored) -> list[TableData]:
    random.seed(seed)
    rng = random.Random(seed + 1)

    # Parse the bundled 3rd-party market data (full history) in pure Python.
    daily_rows = _parse_daily_rows()
    profile_rows = _parse_profile_rows()
    print(f"Loaded bundled market data: {len(daily_rows):,} daily prices, {len(profile_rows)} profiles")

    prices = _price_history(daily_rows)
    universe = sorted(prices)
    shocks = _shock_days(prices)
    latest_closes = {t: series[-1] for t, series in prices.items()}
    print(f"Tradable universe: {len(universe)} tickers, "
          f"{sum(len(s) for s in shocks.values())} shock days detected")

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
    risk_by_client = {c["client_id"]: c["risk_rating"] for c in clients}
    print(f"  Generated {len(clients)} clients")

    accounts = []
    for acc_id in range(1, 201):
        client = random.choice(clients)
        accounts.append({
            "account_id": f"ACC-{acc_id:05d}",
            "client_id": client["client_id"],
            "account_type": random.choice(["Brokerage", "Retirement", "Trust", "Institutional"]),
            "status": random.choices(["Active", "Restricted", "Closed"], weights=[90, 7, 3])[0],
            "open_date": (datetime(2019, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d"),
            "initial_funding_usd": round(random.uniform(50_000, 2_000_000), 2),
            "cash_balance_usd": 0.0,  # derived from the trade ledger below
        })

    all_trades = []
    positions_by_account: dict[str, dict[str, _Position]] = {}
    for account in accounts:
        if account["status"] == "Closed":
            account["cash_balance_usd"] = round(account["initial_funding_usd"], 2)
            continue
        # Most baskets include a news-covered ticker so document questions intersect the data
        basket = [rng.choice(NEWS_TICKERS)] if rng.random() < 0.8 else []
        others = [t for t in universe if t not in basket]
        basket += rng.sample(others, k=min(rng.randint(3, 8) - len(basket), len(others)))
        trades, positions, cash = _simulate_account_trades(
            account, risk_by_client[account["client_id"]], basket, prices, shocks, rng
        )
        all_trades.extend(trades)
        positions_by_account[account["account_id"]] = positions
        account["cash_balance_usd"] = round(cash, 2)
    print(f"  Generated {len(accounts)} accounts")

    all_trades.sort(key=lambda t: (t["trade_date"], t["account_id"], t["symbol"]))
    for i, trade in enumerate(all_trades, 1):
        trade["trade_id"] = f"TRD-{i:07d}"
    print(f"  Generated {len(all_trades)} trades")

    holdings = _derive_holdings(positions_by_account, latest_closes)
    print(f"  Generated {len(holdings)} holdings")

    first_party = {
        "clients": clients,
        "accounts": accounts,
        "trades": all_trades,
        "portfolio_holdings": holdings,
    }
    result = [TableData(name=t, columns=COLUMNS[t], rows=first_party[t]) for t in FIRST_PARTY_TABLES]
    result.append(BundledCsvTable(DAILY_PRICE_TABLE, COLUMNS["dailyprice"], daily_rows))
    result.append(BundledCsvTable(COMPANY_PROFILE_TABLE, COLUMNS["company_profile"], profile_rows))
    return result
