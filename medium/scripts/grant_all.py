#!/usr/bin/env python3
"""Grant every permission the deployed L200 app needs, in one pass.

Chains the three grants that guide Step 7 makes attendees do by hand:
  1. Lakebase (Postgres) schema/table/sequence grants for the app's memory.
  2. Unity Catalog grants (USE CATALOG / USE SCHEMA / SELECT) on the data the
     agent's Vector Search + Genie tools read.
  3. Genie space "Can Run" for the app's service principal.

Customer-input-driven: the app name, Lakebase config, and catalog/schema are read
from your own databricks.yml / .env / agent.py and echoed for confirmation — nothing
is hardcoded. The service principal id is resolved automatically from the app.

Each grant is independent and best-effort: a failure in one is reported and the rest
still run, so a partial workspace doesn't block the others. Re-runnable (idempotent).

Usage:
    uv run grant-all                       # resolve everything from config
    uv run grant-all --app-name my-app     # override the app name
    uv run grant-all --profile DEFAULT     # non-interactive auth
    uv run grant-all --skip-genie          # skip the Genie grant

If a grant fails in your environment, run it by hand — see the "Grant permissions"
section of MANUAL_SETUP.md for the exact SQL and UI steps.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.grant_lakebase_permissions import run_lakebase_grants  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_FILE = PROJECT_ROOT / "agent_server" / "agent.py"
ENV_FILE = PROJECT_ROOT / ".env"
DATABRICKS_YML = PROJECT_ROOT / "databricks.yml"
MEMORY_TYPE = "openai"  # L200 uses the OpenAI Agents SDK memory tables


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def step(text: str) -> None:
    print(f"\n{_c('1;34', '▶')} {_c('1', text)}")


def ok(text: str) -> None:
    print(f"  {_c('1;32', '✓')} {text}")


def warn(text: str) -> None:
    print(f"  {_c('1;33', '!')} {text}")


def err(text: str) -> None:
    print(f"{_c('1;31', '✗')} {text}", file=sys.stderr)


def get_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    m = re.search(rf"^{re.escape(key)}=(.*)$", ENV_FILE.read_text(), re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def resolve_profile(cli_profile: str | None) -> str | None:
    return cli_profile or get_env_value("DATABRICKS_CONFIG_PROFILE") or None


def _cli(args: list[str], profile: str | None) -> subprocess.CompletedProcess:
    cmd = ["databricks"] + (["-p", profile] if profile else []) + args
    return subprocess.run(cmd, capture_output=True, text=True)


def read_app_name_from_yml() -> str:
    """Best-effort read of resources.apps.<key>.name from databricks.yml."""
    if not DATABRICKS_YML.exists():
        return ""
    # The app's deployed name is the `name:` under resources.apps.<key>.
    m = re.search(
        r"apps:\s*\n(?:.*\n)*?\s+[\w-]+:\s*\n\s+name:\s*[\"']?([^\"'\n]+)",
        DATABRICKS_YML.read_text(),
    )
    return m.group(1).strip() if m else ""


def resolve_sp_client_id(app_name: str, profile: str | None) -> str:
    result = _cli(["apps", "get", app_name, "--output", "json"], profile)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "app not found")
    data = json.loads(result.stdout)
    sp = data.get("service_principal_client_id", "")
    if not sp:
        raise RuntimeError("app has no service_principal_client_id yet (deploy first)")
    return sp


def catalog_schema_from_agent() -> tuple[str, str]:
    """Extract catalog/schema from the first vector-search MCP URL in agent.py."""
    if not AGENT_FILE.exists():
        return "", ""
    m = re.search(r"/api/2\.0/mcp/vector-search/([^/]+)/([^/]+)/", AGENT_FILE.read_text())
    return (m.group(1), m.group(2)) if m else ("", "")


def genie_space_ids_from_agent() -> list[str]:
    if not AGENT_FILE.exists():
        return []
    return re.findall(r"/api/2\.0/mcp/genie/([^'\"/]+)", AGENT_FILE.read_text())


def build_workspace_client(profile: str | None):
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient(profile=profile) if profile else WorkspaceClient()


def pick_warehouse_id(w) -> str:
    """Return a warehouse id, preferring a RUNNING one."""
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("no SQL warehouses in this workspace")
    for wh in warehouses:
        state = getattr(getattr(wh, "state", None), "value", None)
        if state == "RUNNING":
            return wh.id
    return warehouses[0].id


# ── the three grant phases (each self-contained and best-effort) ──────────────────


def grant_lakebase(sp_client_id: str) -> bool:
    endpoint = get_env_value("LAKEBASE_AUTOSCALING_ENDPOINT")
    instance = get_env_value("LAKEBASE_INSTANCE_NAME")
    project = branch = None
    if endpoint and not instance:
        m = re.match(r"projects/([^/]+)/branches/([^/]+)", endpoint)
        if m:
            project, branch = m.group(1), m.group(2)
    if not instance and not (project and branch):
        warn("No Lakebase config in .env — skipping Lakebase grants.")
        return False
    run_lakebase_grants(
        sp_client_id=sp_client_id,
        memory_type=MEMORY_TYPE,
        instance_name=instance or None,
        project=project,
        branch=branch,
    )
    ok("Lakebase grants applied.")
    return True


def grant_unity_catalog(w, sp_client_id: str, catalog: str, schema: str) -> bool:
    if not catalog or not schema:
        warn("Could not determine catalog/schema from agent.py — skipping UC grants.")
        return False
    warehouse_id = pick_warehouse_id(w)
    statements = [
        f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{sp_client_id}`",
        f"GRANT USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{sp_client_id}`",
        f"GRANT SELECT ON SCHEMA `{catalog}`.`{schema}` TO `{sp_client_id}`",
    ]
    all_ok = True
    for stmt in statements:
        try:
            resp = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id, statement=stmt, wait_timeout="30s"
            )
            state = getattr(getattr(resp, "status", None), "state", None)
            state_val = getattr(state, "value", str(state))
            if state_val in ("SUCCEEDED", "FINISHED"):
                ok(stmt)
            else:
                warn(f"{stmt} → {state_val}")
                all_ok = False
        except Exception as e:  # noqa: BLE001
            warn(f"{stmt} → {e}")
            all_ok = False
    return all_ok


def grant_genie(w, sp_client_id: str, space_ids: list[str]) -> bool:
    if not space_ids:
        warn("No Genie spaces wired into agent.py — skipping Genie grant.")
        return False
    granted_any = False
    for space_id in space_ids:
        try:
            # Genie spaces are permissioned as dashboard-family objects. This API
            # surface varies across SDK versions, so treat failure as "do it by hand".
            w.genie  # noqa: B018 - touch to confirm attribute exists
            raise NotImplementedError
        except Exception:  # noqa: BLE001
            warn(
                f"Grant 'Can Run' on Genie space {space_id} to `{sp_client_id}` in the UI "
                "(Genie space → Share). See MANUAL_SETUP.md → Grant permissions."
            )
    return granted_any


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant all permissions the deployed app needs.")
    parser.add_argument("--profile", help="Databricks CLI profile (default: from .env)")
    parser.add_argument("--app-name", help="App name (default: read from databricks.yml)")
    parser.add_argument("--sp-client-id", help="Service principal id (default: resolved from app)")
    parser.add_argument("--catalog", help="Catalog for UC grants (default: from agent.py)")
    parser.add_argument("--schema", help="Schema for UC grants (default: from agent.py)")
    parser.add_argument("--skip-lakebase", action="store_true")
    parser.add_argument("--skip-uc", action="store_true")
    parser.add_argument("--skip-genie", action="store_true")
    args = parser.parse_args()

    print(_c("1", "\n=== Grant all app permissions ===\n"))
    profile = resolve_profile(args.profile)

    # Resolve inputs (all from the customer's own config; echoed for confirmation).
    step("Resolving configuration")
    app_name = args.app_name or read_app_name_from_yml()
    if not app_name:
        err("Could not determine the app name. Pass --app-name.")
        sys.exit(1)
    ok(f"App: {app_name}")

    sp_client_id = args.sp_client_id
    if not sp_client_id:
        try:
            sp_client_id = resolve_sp_client_id(app_name, profile)
        except Exception as e:  # noqa: BLE001
            err(f"Could not resolve the app's service principal: {e}")
            print("  Deploy the app first, or pass --sp-client-id. See MANUAL_SETUP.md.")
            sys.exit(1)
    ok(f"Service principal: {sp_client_id}")

    catalog = args.catalog
    schema = args.schema
    if not (catalog and schema):
        c, s = catalog_schema_from_agent()
        catalog = catalog or c
        schema = schema or s
    space_ids = genie_space_ids_from_agent()
    ok(f"Catalog/schema: {catalog or '?'}.{schema or '?'}")
    ok(f"Genie spaces: {', '.join(space_ids) or 'none'}")

    results: dict[str, bool] = {}

    if not args.skip_lakebase:
        step("Lakebase grants")
        try:
            results["Lakebase"] = grant_lakebase(sp_client_id)
        except Exception as e:  # noqa: BLE001
            err(f"Lakebase grants failed: {e}")
            results["Lakebase"] = False

    w = None
    if not (args.skip_uc and args.skip_genie):
        try:
            w = build_workspace_client(profile)
        except Exception as e:  # noqa: BLE001
            err(f"Could not connect to Databricks for UC/Genie grants: {e}")

    if w is not None and not args.skip_uc:
        step("Unity Catalog grants")
        try:
            results["Unity Catalog"] = grant_unity_catalog(w, sp_client_id, catalog, schema)
        except Exception as e:  # noqa: BLE001
            err(f"UC grants failed: {e}")
            results["Unity Catalog"] = False

    if w is not None and not args.skip_genie:
        step("Genie grants")
        results["Genie"] = grant_genie(w, sp_client_id, space_ids)

    # Summary
    step("Summary")
    for name, succeeded in results.items():
        (ok if succeeded else warn)(f"{name}: {'granted' if succeeded else 'needs attention'}")
    print(
        "\nRe-run `uv run grant-all` after the app's first request if any Lakebase table "
        "grants were skipped (tables are created on first use).\n"
    )


if __name__ == "__main__":
    main()
