"""Minimal Python-based Data Quality Framework for curated EDGAR output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.contracts import (
    load_contract,
    records_match_contract,
    required_fields_populated,
)
from thesis_proposed_solution.runtime_config import ObjectStorageConfig
from thesis_proposed_solution.storage import build_curated_target


DEFAULT_CONTRACT_PATH = str(Path(__file__).resolve().parents[2] / "contracts" / "edgar_curated_contract.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset-date", required=True)
    parser.add_argument("--curated-bucket", required=True)
    parser.add_argument("--curated-prefix", required=True)
    parser.add_argument("--manifest-bucket", required=True)
    parser.add_argument("--manifest-prefix", required=True)
    parser.add_argument("--release-manifest-ref", required=True)
    parser.add_argument("--terraform-state-ref", required=True)
    parser.add_argument("--change-ref", required=True)
    parser.add_argument("--contract-path", default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--local-base-dir", default=".local-data/object-storage")
    return parser


def _load_json_lines(input_path: Path) -> list[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def evaluate_quality(curated_path: Path, contract_path: str | Path, run_id: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    failed_checks: list[str] = []
    curated_exists = curated_path.exists()
    checks.append(
        {
            "name": "curated_output_exists",
            "passed": curated_exists,
            "details": str(curated_path),
        }
    )
    records: list[dict[str, Any]] = []
    contract = load_contract(contract_path)
    if curated_exists:
        records = _load_json_lines(curated_path)

    schema_matches = False
    schema_errors: list[str] = []
    if curated_exists:
        schema_matches, schema_errors = records_match_contract(records, contract)
    checks.append(
        {
            "name": "schema_matches_contract",
            "passed": schema_matches,
            "details": schema_errors,
        }
    )

    row_count = len(records)
    row_count_check = row_count > 0
    checks.append(
        {
            "name": "row_count_gt_zero",
            "passed": row_count_check,
            "details": row_count,
        }
    )

    required_ids_populated = False
    required_field_errors: list[str] = []
    if curated_exists:
        required_ids_populated, required_field_errors = required_fields_populated(records, contract)
    checks.append(
        {
            "name": "required_ids_non_null",
            "passed": required_ids_populated,
            "details": required_field_errors,
        }
    )

    for check in checks:
        if not check["passed"]:
            failed_checks.append(check["name"])

    return {
        "run_id": run_id,
        "checks": checks,
        "failed_checks": failed_checks,
        "status": "passed" if not failed_checks else "failed",
        "row_count": row_count,
    }


def run_quality_gate(args: argparse.Namespace) -> dict[str, Any]:
    storage_config = ObjectStorageConfig(
        raw_bucket="unused-raw-bucket",
        raw_prefix="unused-raw-prefix",
        curated_bucket=args.curated_bucket,
        curated_prefix=args.curated_prefix,
        manifest_bucket=args.manifest_bucket,
        manifest_prefix=args.manifest_prefix,
        local_base_dir=Path(args.local_base_dir),
    )
    curated_target = build_curated_target(
        storage_config,
        dataset_date=args.dataset_date,
        run_id=args.run_id,
    )
    summary = evaluate_quality(curated_target.local_path, args.contract_path, args.run_id)
    summary["curated_uri"] = curated_target.uri
    summary["curated_path"] = str(curated_target.local_path)
    summary["contract_path"] = str(Path(args.contract_path).resolve())
    summary["release_manifest_ref"] = args.release_manifest_ref
    summary["terraform_state_ref"] = args.terraform_state_ref
    summary["change_ref"] = args.change_ref
    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_quality_gate(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
