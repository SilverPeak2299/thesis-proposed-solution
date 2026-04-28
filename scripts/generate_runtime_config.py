"""Generate a sample local runtime configuration for the governed EDGAR flow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.runtime_config import (
    GoldTableConfig,
    GovernanceRefs,
    ObjectStorageConfig,
    PipelineRuntimeConfig,
    runtime_config_to_dict,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="local_runtime_config.json")
    parser.add_argument(
        "--source-uri",
        default=str(Path("tests/fixtures/edgar_sample/submissions.json").resolve()),
    )
    parser.add_argument("--dataset-date", default="2024-01-31")
    return parser


def build_sample_config(source_uri: str, dataset_date: str) -> PipelineRuntimeConfig:
    return PipelineRuntimeConfig(
        pipeline_id="edgar_governed_pipeline",
        dataset_date=dataset_date,
        source_uri=source_uri,
        object_storage=ObjectStorageConfig(
            raw_bucket="local-raw",
            raw_prefix="edgar/raw",
            curated_bucket="local-curated",
            curated_prefix="edgar/curated",
            manifest_bucket="local-manifests",
            manifest_prefix="governed-runs",
            local_base_dir=Path(".local-data/object-storage"),
            storage_mode="local",
        ),
        gold_table=GoldTableConfig(
            gold_table_bucket="local-gold-bucket",
            gold_namespace="edgar",
            gold_table="filings",
            local_tables_dir=Path(".local-data/s3-tables"),
        ),
        governance=GovernanceRefs(
            release_manifest_ref="release-manifests/dev-edgar-v1.json",
            terraform_state_ref="terraform-state/dev/serial-0001",
            change_ref="issue/EDGAR-1",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = build_sample_config(args.source_uri, args.dataset_date)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(runtime_config_to_dict(config), handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
