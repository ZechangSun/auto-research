from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from auto_research.consolidation import consolidate_memory
from auto_research.improvement import improve_repository
from auto_research.memory import LongTermMemory, MemoryQuery, MemoryRecord, MemoryScope
from auto_research.pipeline import ResearchPipeline
from auto_research.run_state import RunStatus, RunStore


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

    memory = subcommands.add_parser("memory", help="Inspect or update long-term memory.")
    memory_subcommands = memory.add_subparsers(dest="memory_command", required=True)

    remember = memory_subcommands.add_parser("remember", help="Add a memory record.")
    remember.add_argument("content", help="Memory content.")
    remember.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    remember.add_argument("--scope", choices=[scope.value for scope in MemoryScope], default="semantic")
    remember.add_argument("--kind", default="fact")
    remember.add_argument("--importance", type=float, default=0.75)
    remember.add_argument("--confidence", type=float, default=1.0)
    remember.add_argument("--tag", action="append", default=[])

    search = memory_subcommands.add_parser("search", help="Search memory with classical retrieval.")
    search.add_argument("query", help="Search query.")
    search.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    search.add_argument("--scope", action="append", choices=[scope.value for scope in MemoryScope], default=[])
    search.add_argument("--kind", action="append", default=[])
    search.add_argument("--tag", action="append", default=[])
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--json", action="store_true")

    consolidate = memory_subcommands.add_parser("consolidate", help="Promote reusable memories.")
    consolidate.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    consolidate.add_argument("--recent-limit", type=int, default=50)
    consolidate.add_argument("--json", action="store_true")

    runs = subcommands.add_parser("runs", help="Start, resume, and inspect long-running research.")
    run_subcommands = runs.add_subparsers(dest="runs_command", required=True)

    start = run_subcommands.add_parser("start", help="Create a checkpointed research run.")
    start.add_argument("task", help="Research task or coding-agent prompt.")
    start.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    start.add_argument("--state-dir", default=".auto_research/runs", help="Run checkpoint directory.")
    start.add_argument("--max-steps", type=int, default=5)
    start.add_argument("--session-id", default=None)

    step = run_subcommands.add_parser("step", help="Advance a checkpointed run by one step.")
    step.add_argument("run_id", help="Run id to resume.")
    step.add_argument("--db", default=".auto_research/memory.sqlite", help="SQLite memory path.")
    step.add_argument("--state-dir", default=".auto_research/runs", help="Run checkpoint directory.")
    step.add_argument("--json", action="store_true")

    status = run_subcommands.add_parser("status", help="Show a checkpointed run.")
    status.add_argument("run_id", help="Run id to inspect.")
    status.add_argument("--state-dir", default=".auto_research/runs", help="Run checkpoint directory.")
    status.add_argument("--json", action="store_true")

    list_runs = run_subcommands.add_parser("list", help="List checkpointed runs.")
    list_runs.add_argument("--state-dir", default=".auto_research/runs", help="Run checkpoint directory.")
    list_runs.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"run", "improve", "memory", "runs", "-h", "--help"}:
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

    if args.command == "memory":
        return _memory_command(args)

    if args.command == "runs":
        return _runs_command(args)

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


def _runs_command(args: argparse.Namespace) -> int:
    store = RunStore(args.state_dir)
    if args.runs_command == "start":
        memory = LongTermMemory(Path(args.db))
        try:
            state = ResearchPipeline(memory).start(
                args.task,
                max_steps=args.max_steps,
                session_id=args.session_id,
            )
            store.save(state)
            print(f"Started {state.run_id} status={state.status.value}")
        finally:
            memory.close()
        return 0

    if args.runs_command == "step":
        state = store.load(args.run_id)
        if state.status is RunStatus.WAITING:
            state.status = RunStatus.ACTIVE
        memory = LongTermMemory(Path(args.db))
        try:
            state = ResearchPipeline(memory).step(state)
            store.save(state)
            if args.json:
                print(json.dumps(state.to_dict(), indent=2, default=str))
            else:
                report = ResearchPipeline(memory).report_from_state(state)
                print(f"Run {state.run_id} status={state.status.value} steps={state.steps_executed}/{state.max_steps}")
                print(report.to_markdown())
        finally:
            memory.close()
        return 0

    if args.runs_command == "status":
        state = store.load(args.run_id)
        if args.json:
            print(json.dumps(state.to_dict(), indent=2, default=str))
        else:
            print(f"Run {state.run_id} status={state.status.value} steps={state.steps_executed}/{state.max_steps}")
            print(f"Task: {state.task}")
            for step in state.plan.steps:
                print(f"- [{step.status.value}] {step.id}: {step.goal}")
        return 0

    if args.runs_command == "list":
        states = store.list()
        if args.json:
            print(json.dumps([state.to_dict() for state in states], indent=2, default=str))
        else:
            for state in states:
                print(f"{state.run_id} {state.status.value} steps={state.steps_executed}/{state.max_steps} {state.task}")
        return 0
    return 1


def _memory_command(args: argparse.Namespace) -> int:
    memory = LongTermMemory(Path(args.db))
    try:
        if args.memory_command == "remember":
            record = MemoryRecord(
                content=args.content,
                kind=args.kind,
                scope=MemoryScope(args.scope),
                importance=args.importance,
                confidence=args.confidence,
                tags=tuple(args.tag),
            )
            memory.add(record)
            print(f"Remembered {record.id}")
            return 0

        if args.memory_command == "search":
            results = memory.retrieve(
                MemoryQuery(
                    text=args.query,
                    scopes=tuple(MemoryScope(scope) for scope in args.scope),
                    kinds=tuple(args.kind),
                    tags=tuple(args.tag),
                    limit=args.limit,
                )
            )
            if args.json:
                print(json.dumps({"results": [asdict(result) for result in results]}, indent=2, default=str))
            else:
                for result in results:
                    print(
                        f"{result.score:.3f} {result.record.id[:8]} "
                        f"[{result.record.scope.value}/{result.record.kind}] "
                        f"{','.join(result.reasons)}"
                    )
                    print(result.record.content)
            return 0

        if args.memory_command == "consolidate":
            report = consolidate_memory(memory, recent_limit=args.recent_limit)
            if args.json:
                print(json.dumps(asdict(report), indent=2, default=str))
            else:
                print(report.to_markdown())
            return 0
    finally:
        memory.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
