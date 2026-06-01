from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from reproductions.ts_dfm_2511_17229.data import make_synthetic_rows, write_jsonl
from reproductions.ts_dfm_2511_17229.flow import evaluate, train


def load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Install pyyaml with `pip install -e '.[ts-dfm]'`.") from exc
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reproduce TS-DFM arXiv:2511.17229.")
    commands = parser.add_subparsers(dest="command", required=True)

    synthetic = commands.add_parser("make-synthetic", help="Write a tiny synthetic JSONL dataset.")
    synthetic.add_argument("--output", required=True)
    synthetic.add_argument("--count", type=int, default=16)
    synthetic.add_argument("--atoms", type=int, default=5)
    synthetic.add_argument("--seed", type=int, default=7)

    train_cmd = commands.add_parser("train", help="Train the TS-DFM scaffold.")
    train_cmd.add_argument("--config", required=True)

    eval_cmd = commands.add_parser("eval", help="Evaluate a trained checkpoint.")
    eval_cmd.add_argument("--config", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "make-synthetic":
        write_jsonl(args.output, make_synthetic_rows(args.count, args.atoms, args.seed))
        print(f"Wrote {args.output}")
        return 0
    if args.command == "train":
        train(load_yaml(args.config))
        print("Training complete")
        return 0
    if args.command == "eval":
        metrics = evaluate(load_yaml(args.config))
        print(json.dumps(metrics, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
