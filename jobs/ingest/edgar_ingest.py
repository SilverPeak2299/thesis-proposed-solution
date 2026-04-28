"""CLI entrypoint for ingesting a small EDGAR slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.runtime_config import ObjectStorageConfig
from thesis_proposed_solution.storage import (
    build_raw_payload_target,
    build_raw_records_target,
    write_json_lines_target,
    write_json_target,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset-date", required=True)
    parser.add_argument("--source-uri", required=True)
    parser.add_argument("--raw-bucket", required=True)
    parser.add_argument("--raw-prefix", required=True)
    parser.add_argument("--manifest-bucket", required=True)
    parser.add_argument("--manifest-prefix", required=True)
    parser.add_argument("--release-manifest-ref", required=True)
    parser.add_argument("--terraform-state-ref", required=True)
    parser.add_argument("--change-ref", required=True)
    parser.add_argument(
        "--local-base-dir",
        default=".local-data/object-storage",
        help="Local directory used to map bucket/prefix outputs during local execution.",
    )
    parser.add_argument("--storage-mode", choices=("local", "s3"), default="local")
    return parser


def _load_source_text(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    if parsed.scheme in {"http", "https"}:
        with urlopen(source_uri) as response:  # noqa: S310
            return response.read().decode("utf-8")
    if parsed.scheme == "file":
        return Path(parsed.path).read_text(encoding="utf-8")
    return Path(source_uri).read_text(encoding="utf-8")


def _expand_recent_records(recent_filings: dict[str, Any]) -> list[dict[str, Any]]:
    sequence_fields = {
        field_name: values
        for field_name, values in recent_filings.items()
        if isinstance(values, list)
    }
    if not sequence_fields:
        return []

    row_count = len(next(iter(sequence_fields.values())))
    for field_name, values in sequence_fields.items():
        if len(values) != row_count:
            raise ValueError(f"SEC recent filings field {field_name!r} has inconsistent array length")

    records: list[dict[str, Any]] = []
    for index in range(row_count):
        records.append({field_name: values[index] for field_name, values in sequence_fields.items()})
    return records


def _extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("filings"), list):
        return payload["filings"]
    if isinstance(payload.get("filings"), dict):
        recent_filings = payload["filings"].get("recent")
        if isinstance(recent_filings, list):
            return recent_filings
        if isinstance(recent_filings, dict):
            return _expand_recent_records(recent_filings)
    raise ValueError("Unsupported EDGAR payload shape; expected filings or filings.recent records")


def _build_filing_href(record: dict[str, Any], payload: dict[str, Any]) -> str:
    explicit_href = record.get("filingHref")
    if explicit_href:
        return str(explicit_href)

    cik_value = str(record.get("cik") or payload.get("cik") or "").lstrip("0")
    accession_number = str(record.get("accessionNumber") or "")
    primary_document = str(record.get("primaryDocument") or "")
    if cik_value and accession_number and primary_document:
        accession_compact = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik_value}/{accession_compact}/{primary_document}"
    return ""


def _normalize_record(record: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "accession_number": str(record.get("accessionNumber", "")),
        "company_cik": str(record.get("cik") or payload.get("cik") or ""),
        "company_name": str(record.get("companyName") or record.get("name") or payload.get("name") or ""),
        "form_type": str(record.get("formType") or record.get("form") or ""),
        "filing_date": str(record.get("filingDate", "")),
        "source_url": _build_filing_href(record, payload),
    }


def run_ingest(args: argparse.Namespace) -> dict[str, Any]:
    storage_config = ObjectStorageConfig(
        raw_bucket=args.raw_bucket,
        raw_prefix=args.raw_prefix,
        curated_bucket="unused-curated-bucket",
        curated_prefix="unused-curated-prefix",
        manifest_bucket=args.manifest_bucket,
        manifest_prefix=args.manifest_prefix,
        local_base_dir=Path(args.local_base_dir),
        storage_mode=args.storage_mode,
    )
    payload_target = build_raw_payload_target(
        storage_config,
        dataset_date=args.dataset_date,
        run_id=args.run_id,
    )
    records_target = build_raw_records_target(
        storage_config,
        dataset_date=args.dataset_date,
        run_id=args.run_id,
    )

    payload = json.loads(_load_source_text(args.source_uri))
    normalized_records = [_normalize_record(record, payload) for record in _extract_records(payload)]
    write_json_target(payload_target, payload)
    write_json_lines_target(records_target, normalized_records)

    return {
        "run_id": args.run_id,
        "dataset_date": args.dataset_date,
        "source_uri": args.source_uri,
        "raw_payload_uri": payload_target.uri,
        "raw_payload_path": str(payload_target.local_path) if payload_target.local_path else None,
        "raw_records_uri": records_target.uri,
        "raw_records_path": str(records_target.local_path) if records_target.local_path else None,
        "row_count": len(normalized_records),
        "release_manifest_ref": args.release_manifest_ref,
        "terraform_state_ref": args.terraform_state_ref,
        "change_ref": args.change_ref,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_ingest(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
