"""Meridian Capital Partners workshop metadata and UC function."""

from verticals.base import WorkshopVertical
from verticals.financial_services import tables


def _genie_title(schema: str) -> str:
    return f"Financial Services Data ({schema})"


def _udf_sql(full_schema: str) -> str:
    return f"""
CREATE OR REPLACE FUNCTION {full_schema}.weekly_close_spread(ticker_symbol STRING)
RETURNS DOUBLE
RETURN (
  WITH recent_closes AS (
    SELECT date, close
    FROM {full_schema}.dailyprice
    WHERE ticker = ticker_symbol AND close IS NOT NULL
    ORDER BY date DESC
    LIMIT 7
  ),
  daily_returns AS (
    SELECT
      date,
      (close / LAG(close) OVER (ORDER BY date) - 1) * 100 AS daily_return_pct
    FROM recent_closes
  )
  SELECT CASE
    WHEN COUNT(daily_return_pct) < 2 THEN NULL
    ELSE ROUND(STDDEV_SAMP(daily_return_pct), 6)
  END
  FROM daily_returns
)"""


def _generate_extra_kwargs(
    catalog: str,
    schema: str,
    market_data_catalog: str | None,  # unused — market data is bundled with the repo
) -> dict[str, str]:
    return {
        "catalog": catalog,
        "schema": schema,
    }


VERTICAL = WorkshopVertical(
    id="financial_services",
    brand="Meridian Capital Partners",
    genie_title=_genie_title,
    genie_description=(
        "Meridian Capital Partners: clients, accounts, trades, portfolio_holdings, "
        "dailyprice, and company_profile. The trades ledger drives holdings, P&L, and "
        "cash balances; trades execute at real closing prices. Use dailyprice for price "
        "moves around dates; pair with market_news_index (Vector Search) for "
        "historically similar market-shock news."
    ),
    mlflow_experiment_suffix="meridian-agent-workshop",
    generate_tables=tables.generate,
    generate_extra_kwargs=_generate_extra_kwargs,
    table_descriptions=tables.TABLE_DESCRIPTIONS,
    chunk_table_name="market_news_chunked",
    doc_index_name="market_news_index",
    udf_name="weekly_close_spread",
    udf_sql=_udf_sql,
)
