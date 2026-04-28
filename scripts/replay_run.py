"""Replay a previous governed run and verify reproducibility of key outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scripts.run_local_etl import run_pipeline
from thesis_proposed_solution.manifests import load_manifest
from thesis_proposed_solution.runtime_config import apply_runtime_overrides, load_runtime_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("manifest_path")
    parser.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    previous_manifest = load_manifest(args.manifest_path)
    base_config = load_runtime_config(args.config)
    replay_config = apply_runtime_overrides(
        base_config,
        dataset_date=previous_manifest["dataset_date"],
        source_uri=previous_manifest["source_ref"],
        gold_table_bucket=previous_manifest["gold_table_bucket"],
        gold_namespace=previous_manifest["gold_namespace"],
        gold_table=previous_manifest["gold_table"],
        release_manifest_ref=previous_manifest["release_manifest_ref"],
        terraform_state_ref=previous_manifest["terraform_state_ref"],
        change_ref=previous_manifest["change_ref"],
    )
    replay_manifest = run_pipeline(replay_config, run_id=args.run_id)
    reproducible = all(
        [
            replay_manifest["dataset_version"] == previous_manifest["dataset_version"],
            replay_manifest["row_counts"] == previous_manifest["row_counts"],
            replay_manifest["quality_result"]["status"] == previous_manifest["quality_result"]["status"],
            replay_manifest["gold_table_bucket"] == previous_manifest["gold_table_bucket"],
            replay_manifest["gold_namespace"] == previous_manifest["gold_namespace"],
            replay_manifest["gold_table"] == previous_manifest["gold_table"],
        ]
    )
    print(
        json.dumps(
            {
                "previous_manifest_path": args.manifest_path,
                "replay_manifest_path": replay_manifest["manifest_path"],
                "replay_run_id": replay_manifest["run_id"],
                "reproducible": reproducible,
                "dataset_version": replay_manifest["dataset_version"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if reproducible else 1


if __name__ == "__main__":
    raise SystemExit(main())
