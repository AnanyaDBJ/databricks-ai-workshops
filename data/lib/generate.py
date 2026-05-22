"""
Generate workshop data for an industry vertical.

Called from data/01_quickstart_setup.py with the Industry widget value.
"""

import os
from types import SimpleNamespace

from verticals.financial_services import tables as financial_services_tables
from verticals.education import tables as education_tables
from verticals.retail import tables as retail_tables

DATA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDUSTRIES = ("retail", "education", "financial_services")

_CONFIG = {
    "retail": {
        "brand": "FreshMart",
        "genie_title": lambda schema: f"FreshMart_Retail_Data_({schema})",
        "genie_description": (
            "FreshMart grocery retail data. Customers, products, stores, transactions, and payments."
        ),
        "vs_prefix": lambda schema: f"freshmart-vs-{schema.strip().replace('_', '-')}",
        "mlflow_suffix": "freshmart-agent-workshop",
        "udf_sql": None,
        "udf_name": None,
    },
    "education": {
        "brand": "EduPath Academy",
        "genie_title": lambda schema: f"EduPath_Academy_Data_({schema})",
        "genie_description": (
            "EduPath Academy data. Students, courses, campuses, enrollments, and tuition payments."
        ),
        "vs_prefix": lambda schema: f"edupath-vs-{schema.strip().replace('_', '-')}",
        "mlflow_suffix": "edupath-agent-workshop",
        "udf_sql": lambda fs: f"""
CREATE OR REPLACE FUNCTION {fs}.student_forecast(current_students INT, monthly_growth INT)
RETURNS ARRAY<INT>
LANGUAGE PYTHON
AS $$
def f(current_students: int, monthly_growth: int = 10) -> list:
    return [current_students + monthly_growth * i for i in range(1, 7)]
return f(current_students, monthly_growth)
$$""",
        "udf_name": "student_forecast",
    },
    "financial_services": {
        "brand": "Meridian Capital Partners",
        "genie_title": lambda schema: f"Meridian_Capital_Data_({schema})",
        "genie_description": (
            "Meridian Capital Partners data. Clients, instruments, branches, accounts, trades, and settlements."
        ),
        "vs_prefix": lambda schema: f"meridian-vs-{schema.strip().replace('_', '-')}",
        "mlflow_suffix": "meridian-agent-workshop",
        "udf_sql": lambda fs: f"""
CREATE OR REPLACE FUNCTION {fs}.portfolio_forecast(current_aum DOUBLE, monthly_growth_pct DOUBLE)
RETURNS ARRAY<DOUBLE>
LANGUAGE PYTHON
AS $$
def f(current_aum: float, monthly_growth_pct: float = 0.5) -> list:
    return [round(current_aum * (1 + monthly_growth_pct / 100) ** i, 2) for i in range(1, 7)]
return f(current_aum, monthly_growth_pct)
$$""",
        "udf_name": "portfolio_forecast",
    },
}


def _docs_dir(industry: str) -> str:
    return os.path.join(DATA_ROOT, "verticals", industry, "docs")


def generate_workshop_data(industry: str, catalog: str, schema: str, spark, seed: int = 42):
    industry = industry.strip().lower().replace(" ", "_")
    if industry not in INDUSTRIES:
        raise ValueError(f"Unknown industry '{industry}'. Use: {', '.join(INDUSTRIES)}")

    full_schema = f"{catalog}.{schema}"
    cfg = _CONFIG[industry]

    print(f"Generating {cfg['brand']} data in {full_schema}...")

    if industry == "retail":
        tables = retail_tables.generate(spark, full_schema, seed)
    elif industry == "education":
        tables = education_tables.generate(spark, full_schema, seed)
    else:
        tables = financial_services_tables.generate(spark, full_schema, seed)

    udf_sql = cfg["udf_sql"](full_schema) if cfg["udf_sql"] else None

    return SimpleNamespace(
        industry=industry,
        catalog=catalog,
        schema=schema,
        full_schema=full_schema,
        tables=tables,
        docs_dir=_docs_dir(industry),
        brand_name=cfg["brand"],
        genie_title=cfg["genie_title"](schema),
        genie_description=cfg["genie_description"],
        vs_endpoint_prefix=cfg["vs_prefix"](schema),
        mlflow_experiment_suffix=cfg["mlflow_suffix"],
        optional_udf_sql=udf_sql,
        optional_udf_name=cfg["udf_name"],
    )
