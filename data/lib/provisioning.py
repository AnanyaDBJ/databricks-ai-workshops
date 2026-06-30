"""Shared, SDK-based provisioning for the workshop (Vector Search, Genie,
MLflow, optional UC function).

These functions use the Databricks SDK / Vector Search client, which work both
on a cluster (notebook) and from a laptop (CLI), so the workspace notebook and
the local CLI call identical code. Spark is never required here — table writes
flow through the ``SqlTableWriter`` in :mod:`lib.generate`.
"""

from __future__ import annotations

import time

from lib.workspace_links import (
    genie_space_url,
    mlflow_experiment_url,
    print_asset_link,
    uc_function_url,
    vector_search_endpoint_url,
    vector_search_index_catalog_url,
    vector_search_index_url_from_api,
    workspace_host,
)


def ensure_vector_search_index(
    w,
    writer,
    *,
    endpoint_name: str,
    full_schema: str,
    chunk_table: str,
    index_name: str,
    embedding_model: str = "databricks-gte-large-en",
    vector_search_client=None,
    org_id: str | None = None,
) -> str:
    """Create (or reuse) the Vector Search endpoint and a Delta Sync index.

    ``writer`` is used only to enable Change Data Feed on the chunk table.
    Returns the fully-qualified index name.
    """
    from databricks.sdk.service.vectorsearch import EndpointType

    host = workspace_host(w)
    full_index = f"{full_schema}.{index_name}"

    try:
        endpoint = w.vector_search_endpoints.get_endpoint(endpoint_name)
        print(f"Vector Search endpoint '{endpoint_name}' already exists "
              f"(status: {endpoint.endpoint_status.state.value})")
    except Exception:  # noqa: BLE001
        print(f"Creating Vector Search endpoint '{endpoint_name}'...")
        w.vector_search_endpoints.create_endpoint_and_wait(
            name=endpoint_name,
            endpoint_type=EndpointType.STANDARD,
        )
        print(f"Vector Search endpoint '{endpoint_name}' is ONLINE.")
    print_asset_link(
        "Vector Search endpoint",
        vector_search_endpoint_url(host, endpoint_name, org_id),
    )

    status = None
    for attempt in range(60):
        endpoint = w.vector_search_endpoints.get_endpoint(endpoint_name)
        status = endpoint.endpoint_status.state.value
        if status == "ONLINE":
            break
        if attempt % 6 == 0:
            print(f"  Waiting for endpoint to be ONLINE (currently: {status})...")
        time.sleep(10)
    else:
        print(f"WARNING: Endpoint status is '{status}' after 10 minutes. It may still be provisioning.")
    print(f"Endpoint '{endpoint_name}' is ready.")

    writer.exec_sql(
        f"ALTER TABLE {full_schema}.{chunk_table} "
        "SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
    )

    if vector_search_client is None:
        from databricks.ai_search.client import AISearchClient
        vector_search_client = AISearchClient()

    try:
        vector_search_client.delete_index(endpoint_name=endpoint_name, index_name=full_index)
        print(f"Deleted existing index: {full_index}")
    except Exception as e:  # noqa: BLE001
        print(f"No existing index to delete or error occurred: {e}")

    vector_search_client.create_delta_sync_index(
        endpoint_name=endpoint_name,
        source_table_name=f"{full_schema}.{chunk_table}",
        index_name=full_index,
        pipeline_type="TRIGGERED",
        primary_key="chunk_id",
        embedding_source_column="content",
        embedding_model_endpoint_name=embedding_model,
    )
    print(f"Vector Search index '{full_index}' created.")
    index_url = vector_search_index_url_from_api(w, full_index) or vector_search_index_catalog_url(host, full_index)
    print_asset_link("Vector Search index", index_url)
    return full_index


def _first_warehouse_id(w) -> str | None:
    warehouse_id = None
    for wh in w.warehouses.list():
        if wh.state and wh.state.value in ("RUNNING", "STARTING"):
            return wh.id
        if wh.id:
            warehouse_id = wh.id  # fallback to any warehouse
    return warehouse_id


def ensure_genie_space(
    w,
    *,
    title: str,
    description: str,
    table_identifiers: list[str],
    warehouse_id: str | None = None,
    org_id: str | None = None,
) -> str | None:
    """Create (or reuse) a Genie Space over ``table_identifiers``. Returns its id."""
    import json

    host = workspace_host(w)
    warehouse_id = warehouse_id or _first_warehouse_id(w)
    if not warehouse_id:
        print("WARNING: No SQL warehouse found. Skipping Genie Space creation.")
        return None

    existing = w.api_client.do("GET", "/api/2.0/genie/spaces")
    for space in existing.get("spaces", []):
        if space.get("title") == title:
            space_id = space.get("space_id")
            print(f"Genie Space '{title}' already exists (ID: {space_id})")
            print_asset_link("Genie Space", genie_space_url(host, space_id, org_id))
            return space_id

    print(f"Creating Genie Space '{title}'...")
    serialized = json.dumps({
        "version": 2,
        "data_sources": {"tables": [{"identifier": t} for t in sorted(table_identifiers)]},
    })
    response = w.api_client.do("POST", "/api/2.0/genie/spaces", body={
        "title": title,
        "description": description,
        "warehouse_id": warehouse_id,
        "serialized_space": serialized,
    })
    space_id = response.get("space_id")
    print(f"Genie Space created (ID: {space_id})")
    print_asset_link("Genie Space", genie_space_url(host, space_id, org_id))
    return space_id


def ensure_mlflow_experiment(
    *,
    suffix: str,
    username: str,
    tracking_uri: str = "databricks",
    host: str | None = None,
) -> tuple[str, str]:
    """Create (or reuse) an MLflow experiment under the user's home. Returns (name, id)."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    experiment_name = f"/Users/{username}/{suffix}"
    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment and experiment.lifecycle_stage == "active":
            experiment_id = experiment.experiment_id
            print(f"MLflow experiment already exists: {experiment_name} (ID: {experiment_id})")
        else:
            experiment_id = mlflow.create_experiment(experiment_name)
            print(f"MLflow experiment created: {experiment_name} (ID: {experiment_id})")
    except Exception:  # noqa: BLE001
        experiment_id = mlflow.create_experiment(experiment_name)
        print(f"MLflow experiment created: {experiment_name} (ID: {experiment_id})")

    if host:
        print_asset_link("MLflow experiment", mlflow_experiment_url(host, experiment_id))
    return experiment_name, experiment_id


def register_optional_udf(
    writer,
    *,
    udf_sql: str | None,
    udf_name: str | None,
    full_schema: str,
    host: str | None = None,
) -> None:
    """Register the vertical's optional UC function (if any) via the writer."""
    if not udf_sql:
        print("No optional UC function for this industry.")
        return
    print("UC function SQL definition:")
    print(udf_sql.strip())
    writer.exec_sql(udf_sql)
    print(f"Registered UC function: {full_schema}.{udf_name}")
    if host:
        print_asset_link("UC function", uc_function_url(host, full_schema, udf_name))
