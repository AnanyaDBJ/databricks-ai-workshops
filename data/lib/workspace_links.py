"""Build Databricks workspace UI URLs for workshop setup validation."""

from __future__ import annotations

from urllib.parse import quote


def workspace_host(workspace_client) -> str:
    return (workspace_client.config.host or "").rstrip("/")


def notebook_org_id(dbutils) -> str | None:
    try:
        ctx = dbutils.entry_point.getDbutils().notebook().getContext()
        tags = ctx.tags()
        if tags.getOption("orgId").isDefined():
            return tags.getOption("orgId").get()
    except Exception:
        pass
    return None


def _with_org(url: str, org_id: str | None) -> str:
    if not org_id:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}o={org_id}"


def genie_space_url(host: str, space_id: str, org_id: str | None = None) -> str:
    return _with_org(f"{host}/genie/rooms/{space_id}", org_id)


def mlflow_experiment_url(host: str, experiment_id: str) -> str:
    return f"{host}/ml/experiments/{experiment_id}"


def vector_search_endpoint_url(host: str, endpoint_name: str, org_id: str | None = None) -> str:
    return _with_org(f"{host}/compute/vector-search/{quote(endpoint_name, safe='')}", org_id)


def vector_search_index_catalog_url(host: str, index_name: str) -> str:
    """Catalog Explorer link for a three-level index name (catalog.schema.index)."""
    parts = index_name.split(".")
    if len(parts) != 3:
        return f"{host}/explore/data"
    catalog, schema, index = parts
    return f"{host}/explore/data/{quote(catalog, safe='')}/{quote(schema, safe='')}/{quote(index, safe='')}"


def uc_function_url(host: str, full_schema: str, function_name: str) -> str:
    catalog, schema = full_schema.split(".", 1)
    return (
        f"{host}/explore/data/{quote(catalog, safe='')}/"
        f"{quote(schema, safe='')}/functions/{quote(function_name, safe='')}"
    )


def vector_search_index_url_from_api(workspace_client, index_name: str) -> str | None:
    try:
        info = workspace_client.vector_search_indexes.get_index(index_name=index_name)
        for attr in ("index_url", "url"):
            url = getattr(info, attr, None)
            if url:
                return str(url).rstrip("/")
        status = getattr(info, "status", None)
        if status:
            for attr in ("index_url", "url"):
                url = getattr(status, attr, None)
                if url:
                    return str(url).rstrip("/")
    except Exception:
        pass
    return None


def print_asset_link(label: str, url: str) -> None:
    print(f"  Open {label}: {url}")
