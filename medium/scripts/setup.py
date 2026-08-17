#!/usr/bin/env python3
"""One guided, input-driven setup for the L200 workshop.

Runs the setup phases in order, pausing between each so the attendee stays in control
and can see what happened. Each phase is an existing command you can also run on its own:

    1. quickstart        auth, MLflow experiment, Lakebase, .env + databricks.yml
    2. configure-agent   pick your tools; writes agent_server/agent.py
    3. (you) deploy      `databricks bundle deploy` + `bundle run`  ← hands-on, by design
    4. grant-all         Lakebase + Unity Catalog + Genie permissions
    5. preflight         start locally and send one test request

Deploy is left to you on purpose — watching the app deploy is part of the workshop.

Usage:
    uv run setup                    # guided, interactive
    uv run setup --profile DEFAULT  # pass the profile through to quickstart/grant-all

If any phase fails in your environment, run that phase's command by hand, or follow the
matching section of MANUAL_SETUP.md. The phases are independent and re-runnable.
"""

import argparse
import subprocess
import sys


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def header(text: str) -> None:
    print("\n" + _c("1;36", "═" * 60))
    print(_c("1;36", f"  {text}"))
    print(_c("1;36", "═" * 60))


def confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return True
    return input(f"\n{_c('1;33', '?')} {prompt} [Y/n]: ").strip().lower() != "n"


def run_phase(name: str, cmd: list[str]) -> bool:
    header(name)
    print(f"$ {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            _c("1;31", f"\n✗ '{name}' exited with code {result.returncode}.")
            + "\n  Fix the issue and re-run `uv run setup`, run this phase's command on its "
            "own, or follow MANUAL_SETUP.md."
        )
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Guided end-to-end L200 workshop setup.")
    parser.add_argument("--profile", help="Databricks CLI profile passed to quickstart/grant-all")
    args = parser.parse_args()
    profile_flag = ["--profile", args.profile] if args.profile else []

    header("L200 guided setup")
    print(
        "This walks you through every phase. You approve each step, and you run the\n"
        "deploy yourself. Ctrl-C to stop at any point — phases are re-runnable.\n"
    )

    # Phase 1
    if confirm("Run quickstart (auth, experiment, Lakebase, config files)?"):
        if not run_phase("Phase 1 — quickstart", ["uv", "run", "quickstart"] + profile_flag):
            sys.exit(1)

    # Phase 2
    if confirm("Configure the agent (pick tools, write agent.py)?"):
        cmd = ["uv", "run", "configure-agent"] + profile_flag
        if not run_phase("Phase 2 — configure-agent", cmd):
            sys.exit(1)

    # Phase 3 — deploy (hands-on)
    header("Phase 3 — deploy (you run this)")
    print(
        "Deploy the app yourself so you see it happen:\n\n"
        "  databricks bundle validate\n"
        "  databricks bundle deploy\n"
        "  databricks bundle run agent_openai_agents_sdk\n\n"
        "(In a Databricks workspace, run these in the Web Terminal.)"
    )
    if not confirm("Have you deployed the app and is it running?"):
        print("\nRun `uv run setup` again once the app is deployed to finish grants + preflight.")
        sys.exit(0)

    # Phase 4
    if confirm("Grant all permissions (Lakebase + Unity Catalog + Genie)?"):
        run_phase("Phase 4 — grant-all", ["uv", "run", "grant-all"] + profile_flag)

    # Phase 5
    if confirm("Run preflight (local smoke test)?"):
        run_phase("Phase 5 — preflight", ["uv", "run", "preflight"])

    header("Setup complete")
    print("Open your app and try a Vector Search, a Genie, and a memory question.\n")


if __name__ == "__main__":
    main()
