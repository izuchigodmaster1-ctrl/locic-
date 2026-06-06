#!/usr/bin/env python3
"""Central launcher for the locic repository."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

SCRIPT_MAP = {
    "workflow": ROOT / "WorkflowOrchestratorv2.py",
    "pipeline": ROOT / "The Consolidated Pipeline.py",
    "orchestrator": ROOT / "The Orchestrator.py",
    "guardrails": ROOT / "Implement guardrails.py",
    "chatbot": ROOT / "chatbot.py",
    "test": ROOT / "Automated Testing.py",
}


def run_script(script_path: Path, additional_args: list[str]) -> int:
    if not script_path.exists():
        raise FileNotFoundError(f"Could not find script: {script_path}")

    command = [sys.executable, str(script_path), *additional_args]
    result = subprocess.run(command)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repo scripts from a single launcher.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    workflow = subparsers.add_parser("workflow", help="Run the workflow orchestrator.")
    workflow.add_argument("task", help="Task description for code generation.")
    workflow.add_argument("--api-key", help="Optional API key for tooling.")

    guardrails = subparsers.add_parser("guardrails", help="Run the guardrails-enabled workflow.")
    guardrails.add_argument("task", help="Task description for code generation.")
    guardrails.add_argument("--api-key", help="Optional API key for tooling.")

    pipeline = subparsers.add_parser("pipeline", help="Run the consolidated pipeline script.")
    pipeline.add_argument("task", nargs="?", help="Optional task description for the pipeline.")
    pipeline.add_argument("--api-key", help="Optional API key for tooling.")

    orchestrator = subparsers.add_parser("orchestrator", help="Run the legacy orchestrator script.")
    orchestrator.add_argument("task", nargs="?", help="Optional task description for the orchestrator.")
    orchestrator.add_argument("--api-key", help="Optional API key for tooling.")

    chatbot = subparsers.add_parser("chatbot", help="Run the local chatbot.")

    test = subparsers.add_parser("test", help="Run the automated test harness.")
    test.add_argument("--task", help="Optional task description for the test runner.")
    test.add_argument("--output", help="Optional output filename inside the workspace.")
    test.add_argument("--tests", help="Optional pytest test file path.")

    args = parser.parse_args()

    if args.command == "workflow":
        extra = [args.task]
        if args.api_key:
            extra.extend(["--api-key", args.api_key])
        return_code = run_script(SCRIPT_MAP["workflow"], extra)
    elif args.command == "guardrails":
        extra = [args.task]
        if args.api_key:
            extra.extend(["--api-key", args.api_key])
        return_code = run_script(SCRIPT_MAP["guardrails"], extra)
    elif args.command == "pipeline":
        extra: list[str] = []
        if args.task:
            extra.append(args.task)
        if args.api_key:
            extra.extend(["--api-key", args.api_key])
        return_code = run_script(SCRIPT_MAP["pipeline"], extra)
    elif args.command == "orchestrator":
        extra = []
        if args.task:
            extra.append(args.task)
        if args.api_key:
            extra.extend(["--api-key", args.api_key])
        return_code = run_script(SCRIPT_MAP["orchestrator"], extra)
    elif args.command == "chatbot":
        return_code = run_script(SCRIPT_MAP["chatbot"], [])
    elif args.command == "test":
        extra: list[str] = []
        if args.task:
            extra.extend(["--task", args.task])
        if args.output:
            extra.extend(["--output", args.output])
        if args.tests:
            extra.extend(["--tests", args.tests])
        return_code = run_script(SCRIPT_MAP["test"], extra)
    else:
        parser.print_help()
        return_code = 1

    raise SystemExit(return_code)


if __name__ == "__main__":
    main()
