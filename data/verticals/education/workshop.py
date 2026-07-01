"""EduPath Academy workshop metadata and UC function."""

from verticals.base import WorkshopVertical
from verticals.education import tables


def _genie_title(schema: str) -> str:
    return f"EduPath_Academy_Data_({schema})"


def _udf_sql(full_schema: str) -> str:
    return f"""
CREATE OR REPLACE FUNCTION {full_schema}.student_forecast(current_students INT, monthly_growth INT)
RETURNS ARRAY<INT>
LANGUAGE PYTHON
AS $$
def f(current_students: int, monthly_growth: int = 10) -> list:
    return [current_students + monthly_growth * i for i in range(1, 7)]
return f(current_students, monthly_growth)
$$"""


VERTICAL = WorkshopVertical(
    id="education",
    brand="EduPath Academy",
    genie_title=_genie_title,
    genie_description=(
        "Explore EduPath Academy higher-education operations—student enrollment, course offerings, "
        "campus activity, and tuition patterns—in plain English."
    ),
    mlflow_experiment_suffix="edupath-agent-workshop",
    generate_tables=tables.generate,
    table_descriptions=tables.TABLE_DESCRIPTIONS,
    udf_name="student_forecast",
    udf_sql=_udf_sql,
)
