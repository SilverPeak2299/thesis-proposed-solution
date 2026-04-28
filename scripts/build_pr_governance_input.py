"""Build machine-readable PR governance input for CI and OPA checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.github_governance import (
    build_pr_governance_input,
    load_event_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.event_path:
        raise ValueError("--event-path is required when GITHUB_EVENT_PATH is not set")

    payload = load_event_payload(args.event_path)
    governance_input = build_pr_governance_input(payload)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(governance_input, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
