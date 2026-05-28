"""Meridian Capital Partners workshop metadata and UC function."""

from verticals.base import WorkshopVertical
from verticals.financial_services import tables


def _genie_title(schema: str) -> str:
    return f"Meridian_Capital_Data_({schema})"


def _vs_prefix(schema: str) -> str:
    return f"meridian-vs-{schema.strip().replace('_', '-')}"


def _udf_sql(full_schema: str) -> str:
    return f"""
CREATE OR REPLACE FUNCTION {full_schema}.portfolio_forecast(current_aum DOUBLE, monthly_growth_pct DOUBLE)
RETURNS ARRAY<DOUBLE>
LANGUAGE PYTHON
AS $$
def f(current_aum: float, monthly_growth_pct: float = 0.5) -> list:
    return [round(current_aum * (1 + monthly_growth_pct / 100) ** i, 2) for i in range(1, 7)]
return f(current_aum, monthly_growth_pct)
$$"""


def _generate_tables(
    spark,
    full_schema: str,
    seed: int = 42,
    catalog: str | None = None,
    schema: str | None = None,
    market_data_catalog: str | None = None,
):
    workshop_catalog, workshop_schema = (catalog, schema) if catalog and schema else full_schema.split(".", 1)
    return tables.generate(
        spark,
        full_schema,
        seed,
        catalog=workshop_catalog,
        schema=workshop_schema,
        market_data_catalog=market_data_catalog or workshop_catalog,
    )


VERTICAL = WorkshopVertical(
    id="financial_services",
    brand="Meridian Capital Partners",
    genie_title=_genie_title,
    genie_description=(
        "Explore Meridian Capital Partners clients, accounts, portfolio holdings, "
        "dailyprice, and company_profile in this schema."
    ),
    vs_endpoint_prefix=_vs_prefix,
    mlflow_experiment_suffix="meridian-agent-workshop",
    generate_tables=_generate_tables,
    udf_name="portfolio_forecast",
    udf_sql=_udf_sql,
)
