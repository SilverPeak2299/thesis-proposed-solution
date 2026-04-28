"""CLI entrypoint for transforming normalized EDGAR records into curated output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.contracts import coerce_record_to_contract, load_contract
from thesis_proposed_solution.runtime_config import ObjectStorageConfig
from thesis_proposed_solution.storage import (
    build_curated_target,
    build_raw_records_target,
    read_json_lines_target,
    write_json_lines_target,
)

DEFAULT_CONTRACT_PATH = str(Path(__file__).resolve().parents[2] / "contracts" / "edgar_curated_contract.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset-date", required=True)
    parser.add_argument("--raw-bucket", required=True)
    parser.add_argument("--raw-prefix", required=True)
    parser.add_argument("--curated-bucket", required=True)
    parser.add_argument("--curated-prefix", required=True)
    parser.add_argument("--manifest-bucket", required=True)
    parser.add_argument("--manifest-prefix", required=True)
    parser.add_argument("--release-manifest-ref", required=True)
    parser.add_argument("--terraform-state-ref", required=True)
    parser.add_argument("--change-ref", required=True)
    parser.add_argument("--contract-path", default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--local-base-dir", default=".local-data/object-storage")
    parser.add_argument("--storage-mode", choices=("local", "s3"), default="local")
    return parser


def _curate_record(record: dict[str, Any], *, dataset_date: str, run_id: str) -> dict[str, Any]:
    return {
        "accession_number": record.get("accession_number"),
        "company_cik": record.get("company_cik"),
        "company_name": record.get("company_name"),
        "form_type": record.get("form_type"),
        "filing_date": record.get("filing_date"),
        "source_url": record.get("source_url"),
        "dataset_date": dataset_date,
        "run_id": run_id,
    }


def run_transform(args: argparse.Namespace) -> dict[str, Any]:
    storage_config = ObjectStorageConfig(
        raw_bucket=args.raw_bucket,
        raw_prefix=args.raw_prefix,
        curated_bucket=args.curated_bucket,
        curated_prefix=args.curated_prefix,
        manifest_bucket=args.manifest_bucket,
        manifest_prefix=args.manifest_prefix,
        local_base_dir=Path(args.local_base_dir),
        storage_mode=args.storage_mode,
    )
    raw_records_target = build_raw_records_target(
        storage_config,
        dataset_date=args.dataset_date,
        run_id=args.run_id,
    )
    curated_target = build_curated_target(
        storage_config,
        dataset_date=args.dataset_date,
        run_id=args.run_id,
    )
    contract = load_contract(args.contract_path)
    raw_records = read_json_lines_target(raw_records_target)
    curated_records = [
        coerce_record_to_contract(
            _curate_record(record, dataset_date=args.dataset_date, run_id=args.run_id),
            contract,
        )
        for record in raw_records
    ]
    write_json_lines_target(curated_target, curated_records)
    return {
        "run_id": args.run_id,
        "dataset_date": args.dataset_date,
        "raw_records_uri": raw_records_target.uri,
        "raw_records_path": str(raw_records_target.local_path) if raw_records_target.local_path else None,
        "curated_uri": curated_target.uri,
        "curated_path": str(curated_target.local_path) if curated_target.local_path else None,
        "contract_path": str(Path(args.contract_path).resolve()),
        "row_count": len(curated_records),
        "release_manifest_ref": args.release_manifest_ref,
        "terraform_state_ref": args.terraform_state_ref,
        "change_ref": args.change_ref,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_transform(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
