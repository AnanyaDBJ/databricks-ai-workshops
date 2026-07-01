"""Shared types for industry vertical workshop setup."""

from dataclasses import dataclass
from typing import Any, Callable

# (column_name, sql_type) pairs, e.g. ("price", "DOUBLE").
Columns = list[tuple[str, str]]


@dataclass
class TableData:
    """A table to materialize: a name, an explicit schema, and rows.

    ``rows`` are dicts keyed by column name. A *writer* (see
    :class:`lib.generate.SqlTableWriter`) turns this into ``CREATE OR REPLACE
    TABLE`` + batched ``INSERT`` statements. The generation logic in ``lib/``
    and ``verticals/`` only ever produces ``TableData`` — it never touches Spark
    or any execution backend.
    """

    name: str
    columns: Columns
    rows: list[dict]

    @property
    def column_names(self) -> list[str]:
        return [c for c, _ in self.columns]

    def ddl(self) -> str:
        return ", ".join(f"`{c}` {t}" for c, t in self.columns)

    def row_tuples(self) -> list[tuple]:
        names = self.column_names
        return [tuple(r.get(n) for n in names) for r in self.rows]


def BundledCsvTable(name: str, columns: Columns, rows: list[dict]) -> TableData:  # noqa: N802
    """A reference table sourced from a CSV bundled with the repo.

    Kept as a self-documenting alias for :class:`TableData` (the data loads the
    same way as any other table).
    """
    return TableData(name=name, columns=columns, rows=rows)


# Short codes for Vector Search endpoint names: {code}-vs-{schema}
VS_ENDPOINT_SLUGS: dict[str, str] = {
    "retail": "retail",
    "education": "education",
    "financial_services": "fsi",
}


def vs_endpoint_name(vertical_id: str, schema: str) -> str:
    key = vertical_id.strip().lower().replace(" ", "_")
    try:
        slug = VS_ENDPOINT_SLUGS[key]
    except KeyError:
        known = ", ".join(sorted(VS_ENDPOINT_SLUGS))
        raise ValueError(
            f"Unknown industry '{vertical_id}'. Add it to VS_ENDPOINT_SLUGS or use: {known}"
        ) from None
    schema_slug = schema.strip().replace("_", "-")
    return f"{slug}-vs-{schema_slug}"


@dataclass(frozen=True)
class WorkshopVertical:
    """Metadata and generators for one workshop industry."""

    id: str
    brand: str
    genie_title: Callable[[str], str]
    genie_description: str
    mlflow_experiment_suffix: str
    generate_tables: Callable[..., list]  # returns list[verticals.base.TableData]
    generate_extra_kwargs: Callable[[str, str, str | None], dict[str, Any]] | None = None
    table_descriptions: dict[str, str] | None = None
    chunk_table_name: str = "policy_docs_chunked"
    doc_index_name: str = "policy_docs_index"
    udf_name: str | None = None
    udf_sql: Callable[[str], str] | None = None
