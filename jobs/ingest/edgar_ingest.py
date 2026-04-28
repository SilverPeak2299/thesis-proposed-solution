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
from thesis_proposed_solution.storage import build_raw_payload_target, build_raw_records_target


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
    return parser


def _load_source_text(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    if parsed.scheme in {"http", "https"}:
        with urlopen(source_uri) as response:  # noqa: S310
            return response.read().decode("utf-8")
    if parsed.scheme == "file":
        return Path(parsed.path).read_text(encoding="utf-8")
    return Path(source_uri).read_text(encoding="utf-8")


def _extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("filings"), list):
        return payload["filings"]
    if isinstance(payload.get("filings"), dict) and isinstance(payload["filings"].get("recent"), list):
        return payload["filings"]["recent"]
    raise ValueError("Unsupported EDGAR sample format; expected a top-level filings list")


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "accession_number": str(record.get("accessionNumber", "")),
        "company_cik": str(record.get("cik", "")),
        "company_name": str(record.get("companyName", "")),
        "form_type": str(record.get("formType", "")),
        "filing_date": str(record.get("filingDate", "")),
        "source_url": str(record.get("filingHref", "")),
    }


def _write_json(output_path: Path, payload: Any) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_json_lines(output_path: Path, records: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def run_ingest(args: argparse.Namespace) -> dict[str, Any]:
    storage_config = ObjectStorageConfig(
        raw_bucket=args.raw_bucket,
        raw_prefix=args.raw_prefix,
        curated_bucket="unused-curated-bucket",
        curated_prefix="unused-curated-prefix",
        manifest_bucket=args.manifest_bucket,
        manifest_prefix=args.manifest_prefix,
        local_base_dir=Path(args.local_base_dir),
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
    normalized_records = [_normalize_record(record) for record in _extract_records(payload)]
    _write_json(payload_target.local_path, payload)
    _write_json_lines(records_target.local_path, normalized_records)

    return {
        "run_id": args.run_id,
        "dataset_date": args.dataset_date,
        "source_uri": args.source_uri,
        "raw_payload_uri": payload_target.uri,
        "raw_payload_path": str(payload_target.local_path),
        "raw_records_uri": records_target.uri,
        "raw_records_path": str(records_target.local_path),
        "row_count": len(normalized_records),
        "release_manifest_ref": args.release_manifest_ref,
        "terraform_state_ref": args.terraform_state_ref,
        "change_ref": args.change_ref,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_ingest(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
