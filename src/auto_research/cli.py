from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from auto_research.improvement import improve_repository
from auto_research.memory import LongTermMemory
from auto_research.pipeline import ResearchPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an auto-research pipeline.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="Run research for a task.")
    run.add_argument("task", help="Research task or coding-agent prompt.")
    run.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    run.add_argument("--max-steps", type=int, default=5, help="Maximum research steps to run.")
    run.add_argument("--session-id", default=None, help="Optional stable session id.")
    run.add_argument("--json", action="store_true", help="Print a structured JSON report.")

    improve = subcommands.add_parser("improve", help="Research improvements for a repository.")
    improve.add_argument("--repo", default=".", help="Repository path to inspect.")
    improve.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    improve.add_argument("--max-steps", type=int, default=5, help="Maximum research steps to run.")
    improve.add_argument("--session-id", default="repo-improvement", help="Stable session id.")
    improve.add_argument(
        "--output",
        default=".auto_research/improvement_brief.md",
        help="Where to write the improvement brief.",
    )
    improve.add_argument("--json", action="store_true", help="Print a structured JSON report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"run", "improve", "-h", "--help"}:
        argv.insert(0, "run")

    args = build_parser().parse_args(argv)
    if args.command == "improve":
        result = improve_repository(
            repo_path=Path(args.repo),
            db_path=Path(args.db),
            max_steps=args.max_steps,
            session_id=args.session_id,
            output_path=Path(args.output),
        )
        if args.json:
            print(json.dumps(asdict(result), indent=2, default=str))
        else:
            print(result.report.to_markdown())
            print(f"\nImprovement brief written to {result.output_path}")
        return 0

    memory = LongTermMemory(Path(args.db))
    try:
        report = ResearchPipeline(memory).run(
            task=args.task,
            max_steps=args.max_steps,
            session_id=args.session_id,
        )
        if args.json:
            print(json.dumps(asdict(report), indent=2, default=str))
        else:
            print(report.to_markdown())
    finally:
        memory.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
