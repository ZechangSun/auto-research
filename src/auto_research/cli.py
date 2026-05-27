from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from auto_research.memory import LongTermMemory
from auto_research.pipeline import ResearchPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an auto-research pipeline.")
    parser.add_argument("task", help="Research task or coding-agent prompt.")
    parser.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum research steps to run.")
    parser.add_argument("--session-id", default=None, help="Optional stable session id.")
    parser.add_argument("--json", action="store_true", help="Print a structured JSON report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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

