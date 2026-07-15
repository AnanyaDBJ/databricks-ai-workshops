"""
Generate workshop data for an industry vertical.

Spark-free core: verticals return ``TableData`` and a *writer* persists them.
The single :class:`SqlTableWriter` (defined here) runs identically from the
workshop notebook (on a cluster) and the local CLI (from a laptop) — both
authenticate through a ``WorkspaceClient`` and write via the SQL Statement
Execution API. Called from the setup entrypoints with the Industry value.
"""

import os
import sys
import time
from types import SimpleNamespace

from verticals.base import TableData, vs_endpoint_name
from verticals.registry import INDUSTRIES, get_vertical  # noqa: F401 — re-exported for CLI/scripts

DATA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

__all__ = ["INDUSTRIES", "SqlTableWriter", "generate_workshop_data"]


def _sql_literal(value, sql_type: str) -> str:
    if value is None:
        return "NULL"
    t = sql_type.strip().upper()
    if t in ("INT", "INTEGER", "BIGINT", "LONG", "SMALLINT", "TINYINT"):
        return str(int(value))
    if t in ("DOUBLE", "FLOAT", "REAL") or t.startswith("DECIMAL"):
        return repr(float(value))
    if t == "BOOLEAN":
        return "TRUE" if value else "FALSE"
    if t in ("DATE", "TIMESTAMP"):
        return "'" + str(value) + "'"
    # STRING and anything else: quote and escape.
    text = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{text}'"


class SqlTableWriter:
    """Persist tables via the SQL Statement Execution API (notebook or CLI).

    Owns a ``WorkspaceClient`` so the same code authenticates on a Databricks
    cluster (ambient auth) or from a laptop (a CLI profile). Every table is
    created with ``CREATE OR REPLACE TABLE`` and populated with batched
    ``INSERT`` statements — no Spark, UC Volume, or ``COPY INTO``.
    """

    def __init__(self, w, warehouse_id: str):
        self.w = w
        self.warehouse_id = warehouse_id

    @classmethod
    def from_profile(cls, profile: str, warehouse_id: str | None = None) -> "SqlTableWriter":
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient(profile=profile)
        if not warehouse_id:
            from lib.provisioning import _first_warehouse_id

            warehouse_id = _first_warehouse_id(w)
            if not warehouse_id:
                raise ValueError(
                    "No SQL warehouse found. Start a SQL warehouse or pass --warehouse-id."
                )
        return cls(w, warehouse_id)

    @property
    def host(self) -> str:
        return (self.w.config.host or "").rstrip("/")

    @property
    def token(self) -> str:
        """A bearer token valid for the client's auth (PAT or OAuth)."""
        headers = self.w.config.authenticate()
        return headers.get("Authorization", "").removeprefix("Bearer ")

    # ── SQL execution ───────────────────────────────────────────────────
    def _execute(self, statement: str):
        from databricks.sdk.service.sql import StatementState

        resp = self.w.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=statement,
            wait_timeout="50s",
        )
        polls = 0
        while (
            resp.status
            and resp.status.state in (StatementState.PENDING, StatementState.RUNNING)
            and resp.statement_id
            and polls < 150
        ):
            time.sleep(2)
            polls += 1
            resp = self.w.statement_execution.get_statement(resp.statement_id)
        return resp

    def exec_sql(self, statement: str) -> str:
        resp = self._execute(statement)
        state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
        if state == "FAILED":
            err = resp.status.error.message if resp.status and resp.status.error else ""
            print(f"  SQL FAILED: {err}", file=sys.stderr)
        return state

    def query(self, statement: str) -> list[list]:
        """Run a SELECT and return its rows as a list of value lists."""
        resp = self._execute(statement)
        if resp.result and resp.result.data_array:
            return resp.result.data_array
        return []

    # ── table writes ────────────────────────────────────────────────────
    def write_table(self, full_schema: str, table: TableData) -> None:
        fqn = f"{full_schema}.{table.name}"
        self.exec_sql(f"CREATE OR REPLACE TABLE {fqn} ({table.ddl()})")
        self._insert_rows(fqn, table)

    def _insert_rows(self, fqn: str, table: TableData, batch_size: int = 100) -> None:
        col_str = ", ".join(f"`{c}`" for c, _ in table.columns)
        values = [
            "(" + ", ".join(_sql_literal(row.get(c), t) for c, t in table.columns) + ")"
            for row in table.rows
        ]
        total = 0
        n_batches = (len(values) - 1) // batch_size + 1 if values else 0
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            stmt = f"INSERT INTO {fqn} ({col_str}) VALUES {', '.join(batch)}"
            state = self.exec_sql(stmt)
            if state == "SUCCEEDED":
                total += len(batch)
            else:
                print(f"    Stopping inserts for {fqn} after failure", file=sys.stderr)
                break
            print(f"  {fqn}: batch {i // batch_size + 1}/{n_batches} ({total}/{len(values)})")
        print(f"  Inserted {total:,} rows into {fqn}")


def _docs_dir(industry: str) -> str:
    return os.path.join(DATA_ROOT, "verticals", industry, "docs")


def _apply_table_descriptions(
    writer,
    full_schema: str,
    tables: list[str],
    descriptions: dict[str, str] | None,
) -> None:
    if not descriptions:
        print("No table descriptions configured for this industry; skipping COMMENT ON TABLE.")
        return

    for table in tables:
        description = descriptions.get(table)
        if not description:
            print(f"WARNING: No table description configured for {full_schema}.{table}; skipping.")
            continue

        escaped = description.replace("'", "''")
        writer.exec_sql(f"COMMENT ON TABLE {full_schema}.{table} IS '{escaped}'")
        print(f"  Added table description: {full_schema}.{table}")


def generate_workshop_data(
    industry: str,
    catalog: str,
    schema: str,
    writer,
    seed: int = 42,
    market_data_catalog: str | None = None,
):
    """Generate and persist all structured tables for ``industry``.

    ``writer`` is a :class:`SqlTableWriter` (used by both the notebook and CLI).
    """
    if writer is None:
        raise ValueError("generate_workshop_data requires a `writer`.")

    vertical = get_vertical(industry)
    full_schema = f"{catalog}.{schema}"

    print(f"Generating {vertical.brand} data in {full_schema}...")

    gen_kwargs: dict = {"seed": seed}
    if vertical.generate_extra_kwargs:
        gen_kwargs.update(vertical.generate_extra_kwargs(catalog, schema, market_data_catalog))

    table_datas = vertical.generate_tables(**gen_kwargs)
    for table in table_datas:
        writer.write_table(full_schema, table)

    tables = [t.name for t in table_datas]
    _apply_table_descriptions(writer, full_schema, tables, vertical.table_descriptions)

    udf_sql = vertical.udf_sql(full_schema) if vertical.udf_sql else None

    return SimpleNamespace(
        industry=vertical.id,
        catalog=catalog,
        schema=schema,
        full_schema=full_schema,
        tables=tables,
        docs_dir=_docs_dir(vertical.id),
        brand_name=vertical.brand,
        genie_title=vertical.genie_title(schema),
        genie_description=vertical.genie_description,
        vs_endpoint_name=vs_endpoint_name(vertical.id, schema),
        chunk_table_name=vertical.chunk_table_name,
        doc_index_name=vertical.doc_index_name,
        mlflow_experiment_suffix=vertical.mlflow_experiment_suffix,
        optional_udf_sql=udf_sql,
        optional_udf_name=vertical.udf_name,
    )
