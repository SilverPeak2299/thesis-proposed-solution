"""Governed promotion step that writes approved curated data into an S3 Table target."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.manifests import canonical_json, compute_dataset_version
from thesis_proposed_solution.runtime_config import GoldTableConfig, ObjectStorageConfig
from thesis_proposed_solution.storage import (
    build_curated_target,
    build_gold_table_directory,
    build_gold_table_uri,
    read_json_lines_target,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset-date", required=True)
    parser.add_argument("--curated-bucket", required=True)
    parser.add_argument("--curated-prefix", required=True)
    parser.add_argument("--manifest-bucket", required=True)
    parser.add_argument("--manifest-prefix", required=True)
    parser.add_argument("--gold-table-bucket", required=True)
    parser.add_argument("--gold-namespace", required=True)
    parser.add_argument("--gold-table", required=True)
    parser.add_argument("--release-manifest-ref", required=True)
    parser.add_argument("--terraform-state-ref", required=True)
    parser.add_argument("--change-ref", required=True)
    parser.add_argument("--local-base-dir", default=".local-data/object-storage")
    parser.add_argument("--local-tables-dir", default=".local-data/s3-tables")
    parser.add_argument("--storage-mode", choices=("local", "s3"), default="local")
    return parser


def _write_json_lines(output_path: Path, records: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=False))
            handle.write("\n")


def run_promotion(args: argparse.Namespace) -> dict[str, Any]:
    storage_config = ObjectStorageConfig(
        raw_bucket="unused-raw-bucket",
        raw_prefix="unused-raw-prefix",
        curated_bucket=args.curated_bucket,
        curated_prefix=args.curated_prefix,
        manifest_bucket=args.manifest_bucket,
        manifest_prefix=args.manifest_prefix,
        local_base_dir=Path(args.local_base_dir),
        storage_mode=args.storage_mode,
    )
    gold_config = GoldTableConfig(
        gold_table_bucket=args.gold_table_bucket,
        gold_namespace=args.gold_namespace,
        gold_table=args.gold_table,
        local_tables_dir=Path(args.local_tables_dir),
    )

    curated_target = build_curated_target(
        storage_config,
        dataset_date=args.dataset_date,
        run_id=args.run_id,
    )
    records = read_json_lines_target(curated_target)
    promoted_records = [{key: value for key, value in record.items() if key != "run_id"} for record in records]
    content_digest = hashlib.sha256(canonical_json(promoted_records).encode("utf-8")).hexdigest()
    version_input = {
        "dataset_date": args.dataset_date,
        "row_count": len(records),
        "content_digest": content_digest,
        "write_mode": "append",
    }
    dataset_version = compute_dataset_version(
        gold_table_bucket=gold_config.gold_table_bucket,
        gold_namespace=gold_config.gold_namespace,
        gold_table=gold_config.gold_table,
        write_result=version_input,
    )
    write_result = dict(version_input)
    write_result["source_curated_uri"] = curated_target.uri
    table_dir = build_gold_table_directory(
        gold_config,
        dataset_date=args.dataset_date,
        dataset_version=dataset_version,
    )
    records_path = table_dir / "records.jsonl"
    write_result_path = table_dir / "write-result.json"
    _write_json_lines(records_path, promoted_records)
    write_result["table_uri"] = build_gold_table_uri(gold_config)
    write_result["records_path"] = str(records_path)
    write_result["write_result_path"] = str(write_result_path)
    write_result_path.parent.mkdir(parents=True, exist_ok=True)
    with write_result_path.open("w", encoding="utf-8") as handle:
        json.dump(write_result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return {
        "run_id": args.run_id,
        "dataset_date": args.dataset_date,
        "curated_uri": curated_target.uri,
        "curated_path": str(curated_target.local_path) if curated_target.local_path else None,
        "gold_table_bucket": gold_config.gold_table_bucket,
        "gold_namespace": gold_config.gold_namespace,
        "gold_table": gold_config.gold_table,
        "dataset_version": dataset_version,
        "row_count": len(promoted_records),
        "gold_write_result": write_result,
        "release_manifest_ref": args.release_manifest_ref,
        "terraform_state_ref": args.terraform_state_ref,
        "change_ref": args.change_ref,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_promotion(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
