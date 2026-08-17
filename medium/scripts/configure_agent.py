#!/usr/bin/env python3
"""Interactive agent configurator for the L200 workshop.

Wires the tools an attendee picks into ``agent_server/agent.py`` so nobody has to
hand-build ``/api/2.0/mcp/...`` URLs or convert dots to slashes. The attendee still
*chooses* the tools and writes the system prompt — that is the part they should learn.
Everything else (URL format, GENERATED block editing, model env vars) is handled here.

Customer-input-driven: nothing is hardcoded. The wizard prompts for every value, and
for tools it lists what actually exists in the connected workspace and lets the
attendee select. Re-runnable (idempotent) — it rewrites only the GENERATED block.

Usage:
    uv run configure-agent                       # fully interactive
    uv run configure-agent --profile DEFAULT     # non-interactive auth
    uv run configure-agent --name my-agent --system-prompt "You are ..." \
        --vector-index cat.schema.idx --genie-space 01abc... \
        --model databricks-claude-opus-4-6        # scriptable / CI

If discovery or any step fails in your environment, configure the GENERATED block by
hand — see the "Configure the agent" section of MANUAL_SETUP.md.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# scripts/ is a package sibling of agent_server/; make sibling imports work when run
# both as `uv run configure-agent` and as `python scripts/configure_agent.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.discover_tools import (  # noqa: E402
    discover_genie_spaces,
    discover_uc_functions,
    discover_vector_search_indexes,
)

AGENT_FILE = Path(__file__).resolve().parent.parent / "agent_server" / "agent.py"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

GENERATED_START = "# GENERATED"
GENERATED_END = "# END GENERATED"

# ── tiny presentation helpers (self-contained; no cross-script coupling) ──────────


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


# ── .env read/write (preserves position of commented placeholders) ────────────────


def get_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    match = re.search(rf"^{re.escape(key)}=(.*)$", ENV_FILE.read_text(), re.MULTILINE)
    return match.group(1).strip().strip('"').strip("'") if match else ""


def update_env_value(key: str, value: str) -> None:
    """Set KEY=value in .env, replacing a commented placeholder in place if present."""
    if not ENV_FILE.exists():
        ENV_FILE.write_text(f"{key}={value}\n")
        return
    content = ENV_FILE.read_text()
    active = rf"^{re.escape(key)}=.*$"
    commented = rf"^#\s*{re.escape(key)}=.*$"
    if re.search(commented, content, re.MULTILINE):
        pos = re.search(commented, content, re.MULTILINE).start()
        content = re.sub(commented + r"\n?", "", content, flags=re.MULTILINE)
        content = re.sub(active + r"\n?", "", content, flags=re.MULTILINE)
        content = content[:pos] + f"{key}={value}\n" + content[pos:]
    elif re.search(active, content, re.MULTILINE):
        content = re.sub(active, f"{key}={value}", content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + f"\n{key}={value}\n"
    ENV_FILE.write_text(content)


# ── prompting ─────────────────────────────────────────────────────────────────────


def ask(prompt: str, default: str = "") -> str:
    if not sys.stdin.isatty():
        return default
    suffix = f" [{default}]" if default else ""
    answer = input(f"  {prompt}{suffix}: ").strip()
    return answer or default


def choose(items: list[dict], label_key: str, id_key: str, what: str) -> list[dict]:
    """Show a numbered list and return the selected items.

    Selection syntax: comma-separated numbers (e.g. "1,3"), "all", or blank for none.
    """
    if not items:
        warn(f"No {what} found in this workspace — skipping.")
        return []
    print(f"\n  Available {what}:")
    for i, item in enumerate(items, 1):
        extra = f"  ({item[id_key]})" if item.get(id_key) else ""
        print(f"    {i}. {item[label_key]}{extra}")
    if not sys.stdin.isatty():
        return []
    raw = input(
        f"  Select {what} by number (comma-separated, 'all', or Enter to skip): "
    ).strip()
    if not raw:
        return []
    if raw.lower() == "all":
        return items
    picked = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= len(items):
            picked.append(items[int(tok) - 1])
        else:
            warn(f"Ignoring invalid selection '{tok}'.")
    return picked


# ── MCP URL construction ────────────────────────────────────────────────────────


def vector_search_mcp_url(index_full_name: str) -> str:
    """cat.schema.index -> /api/2.0/mcp/vector-search/cat/schema/index."""
    return "/api/2.0/mcp/vector-search/" + index_full_name.replace(".", "/")


def genie_mcp_url(space_id: str) -> str:
    return f"/api/2.0/mcp/genie/{space_id}"


def uc_functions_mcp_url(catalog: str, schema: str) -> str:
    return f"/api/2.0/mcp/functions/{catalog}/{schema}"


# ── agent.py GENERATED block rewrite ──────────────────────────────────────────────


def render_generated_block(
    name: str, system_prompt: str, model_line: str, mcp_servers: list[tuple[str, str]]
) -> str:
    """Render the text that goes between the GENERATED markers (markers included)."""
    if mcp_servers:
        entries = "\n".join(
            f"    ({_py_str(label)}, {_py_str(url)})," for label, url in mcp_servers
        )
        mcp_block = f"MCP_SERVERS = [\n{entries}\n]"
    else:
        mcp_block = (
            "MCP_SERVERS = [\n"
            "    # Add your MCP servers here, e.g.:\n"
            "    # ('Vector Search: <catalog>.<schema>.<index>', "
            "'/api/2.0/mcp/vector-search/<catalog>/<schema>/<index>'),\n"
            "    # ('Genie Space: <name>', '/api/2.0/mcp/genie/<space-id>'),\n"
            "]"
        )
    return (
        f"{GENERATED_START}\n\n"
        f"NAME = {_py_str(name)}\n"
        f"SYSTEM_PROMPT = {_py_str(system_prompt)}\n"
        f"{model_line}\n"
        f"{mcp_block}\n\n"
        f"{GENERATED_END}"
    )


def _py_str(value: str) -> str:
    """Render a Python single-quoted string literal, escaping as needed."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


def extract_model_line(block_text: str) -> str:
    """Return the existing ``MODEL = ...`` line, preserving env-driven form (PR #30)."""
    match = re.search(r"^MODEL = .*$", block_text, re.MULTILINE)
    return match.group(0) if match else "MODEL = os.environ.get('AGENT_MODEL', DEFAULT_MODEL)"


def write_generated_block(new_block: str) -> None:
    source = AGENT_FILE.read_text()
    pattern = re.compile(
        re.escape(GENERATED_START) + r".*?" + re.escape(GENERATED_END), re.DOTALL
    )
    if not pattern.search(source):
        raise SystemExit(
            f"Could not find the {GENERATED_START} / {GENERATED_END} markers in "
            f"{AGENT_FILE}. Configure it by hand — see MANUAL_SETUP.md."
        )
    AGENT_FILE.write_text(pattern.sub(lambda _: new_block, source, count=1))


# ── main flow ─────────────────────────────────────────────────────────────────────


def resolve_profile(cli_profile: str | None) -> str | None:
    return cli_profile or get_env_value("DATABRICKS_CONFIG_PROFILE") or None


def build_workspace_client(profile: str | None):
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient(profile=profile) if profile else WorkspaceClient()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wire discovered tools into agent_server/agent.py (customer-input-driven)."
    )
    parser.add_argument("--profile", help="Databricks CLI profile (default: from .env)")
    parser.add_argument("--name", help="Agent name (non-interactive)")
    parser.add_argument("--system-prompt", help="Agent system prompt (non-interactive)")
    parser.add_argument(
        "--vector-index",
        action="append",
        default=[],
        metavar="CAT.SCHEMA.INDEX",
        help="Vector Search index full name to wire in (repeatable, non-interactive)",
    )
    parser.add_argument(
        "--genie-space",
        action="append",
        default=[],
        metavar="SPACE_ID",
        help="Genie space id to wire in (repeatable, non-interactive)",
    )
    parser.add_argument("--model", help="AGENT_MODEL value to write to .env (non-interactive)")
    parser.add_argument(
        "--use-ai-gateway",
        choices=["true", "false"],
        help="AGENT_USE_AI_GATEWAY value to write to .env (non-interactive)",
    )
    args = parser.parse_args()

    if not AGENT_FILE.exists():
        err(f"{AGENT_FILE} not found. Run this from the medium/ project root.")
        sys.exit(1)

    print(_c("1", "\n=== Configure your agent ===\n"))
    print(
        "You choose the tools and the system prompt; this wizard writes the correct\n"
        "MCP URLs and updates agent_server/agent.py for you. Re-run any time.\n"
    )

    # 1) Identity
    step("Agent identity")
    name = args.name or ask("Agent name", "my-agent")
    system_prompt = args.system_prompt or ask(
        "System prompt",
        "You are a helpful assistant for retail store operations. Use the available "
        "tools to answer questions about policies and data.",
    )
    ok(f"Name: {name}")

    # 2) Connect + discover tools
    mcp_servers: list[tuple[str, str]] = []
    if args.vector_index or args.genie_space:
        # Non-interactive path: trust the provided identifiers, build URLs directly.
        for full_name in args.vector_index:
            mcp_servers.append(
                (f"Vector Search: {full_name}", vector_search_mcp_url(full_name))
            )
            ok(f"Vector Search → {vector_search_mcp_url(full_name)}")
        for space_id in args.genie_space:
            mcp_servers.append((f"Genie Space: {space_id}", genie_mcp_url(space_id)))
            ok(f"Genie → {genie_mcp_url(space_id)}")
    else:
        step("Discovering tools in your workspace")
        profile = resolve_profile(args.profile)
        try:
            w = build_workspace_client(profile)
        except Exception as e:  # noqa: BLE001
            err(f"Could not connect to Databricks: {e}")
            print("  Run `uv run quickstart` first, or configure by hand (MANUAL_SETUP.md).")
            sys.exit(1)

        print("  Listing Vector Search indexes...")
        vs = discover_vector_search_indexes(w)
        for idx in choose(vs, "name", "endpoint", "Vector Search indexes"):
            url = vector_search_mcp_url(idx["name"])
            mcp_servers.append((f"Vector Search: {idx['name']}", url))
            ok(f"{idx['name']} → {url}")

        print("  Listing Genie spaces...")
        spaces = discover_genie_spaces(w)
        for sp in choose(spaces, "name", "id", "Genie spaces"):
            url = genie_mcp_url(sp["id"])
            mcp_servers.append((f"Genie Space: {sp['name']}", url))
            ok(f"{sp['name']} → {url}")

        if sys.stdin.isatty() and ask("Add Unity Catalog functions too? (y/N)", "n").lower() == "y":
            print("  Listing UC functions (this can take a moment)...")
            funcs = discover_uc_functions(w)
            for fn in choose(funcs, "name", "comment", "UC functions"):
                url = uc_functions_mcp_url(fn["catalog"], fn["schema"])
                entry = (f"UC Functions: {fn['catalog']}.{fn['schema']}", url)
                if entry not in mcp_servers:
                    mcp_servers.append(entry)
                    ok(f"{fn['name']} → {url}")

    if not mcp_servers:
        warn("No tools selected — the agent will run with no MCP tools until you add some.")

    # 3) Model routing (env-driven since PR #30; written to .env, not agent.py)
    step("Model routing")
    model = args.model or ask("AGENT_MODEL", get_env_value("AGENT_MODEL") or "databricks-claude-opus-4-6")
    use_gw = args.use_ai_gateway or ask(
        "Route through AI Gateway? (true/false)",
        get_env_value("AGENT_USE_AI_GATEWAY") or "false",
    )
    update_env_value("AGENT_MODEL", model)
    update_env_value("AGENT_USE_AI_GATEWAY", use_gw)
    ok(f"AGENT_MODEL={model}, AGENT_USE_AI_GATEWAY={use_gw} written to .env")
    if use_gw.lower() == "true" and model == "databricks-claude-opus-4-6":
        warn(
            "AI Gateway is on but AGENT_MODEL is still the serving-endpoint default. "
            "Point it at your gateway endpoint (often catalog.schema.endpoint)."
        )

    # 4) Rewrite the GENERATED block
    step("Updating agent_server/agent.py")
    current = AGENT_FILE.read_text()
    match = re.search(
        re.escape(GENERATED_START) + r".*?" + re.escape(GENERATED_END), current, re.DOTALL
    )
    model_line = extract_model_line(match.group(0) if match else "")
    block = render_generated_block(name, system_prompt, model_line, mcp_servers)
    write_generated_block(block)
    ok(f"Wrote GENERATED block with {len(mcp_servers)} MCP server(s).")

    print(_c("1;32", "\n✓ Agent configured.") + " Next: `uv run start-app` to test locally.\n")


if __name__ == "__main__":
    main()
