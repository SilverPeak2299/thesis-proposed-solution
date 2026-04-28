"""CLI entrypoint for transforming normalized EDGAR records into curated output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.contracts import coerce_record_to_contract, load_contract
from thesis_proposed_solution.runtime_config import ObjectStorageConfig
from thesis_proposed_solution.storage import build_curated_target, build_raw_records_target


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
    return parser


def _load_json_lines(input_path: Path) -> list[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json_lines(output_path: Path, records: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=False))
            handle.write("\n")


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
    raw_records = _load_json_lines(raw_records_target.local_path)
    curated_records = [
        coerce_record_to_contract(
            _curate_record(record, dataset_date=args.dataset_date, run_id=args.run_id),
            contract,
        )
        for record in raw_records
    ]
    _write_json_lines(curated_target.local_path, curated_records)
    return {
        "run_id": args.run_id,
        "dataset_date": args.dataset_date,
        "raw_records_uri": raw_records_target.uri,
        "raw_records_path": str(raw_records_target.local_path),
        "curated_uri": curated_target.uri,
        "curated_path": str(curated_target.local_path),
        "contract_path": str(Path(args.contract_path).resolve()),
        "row_count": len(curated_records),
        "release_manifest_ref": args.release_manifest_ref,
        "terraform_state_ref": args.terraform_state_ref,
        "change_ref": args.change_ref,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_transform(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
