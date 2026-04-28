from __future__ import annotations

import json
from pathlib import Path

from jobs.quality.curated_quality_gate import evaluate_quality


CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "edgar_curated_contract.json"


def _write_json_lines(output_path: Path, records: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record))
            handle.write("\n")


def test_quality_gate_passes_for_valid_curated_output(tmp_path: Path) -> None:
    curated_path = tmp_path / "curated-records.jsonl"
    _write_json_lines(
        curated_path,
        [
            {
                "accession_number": "0000123456-24-000001",
                "company_cik": "123456",
                "company_name": "Example Holdings Inc",
                "form_type": "10-K",
                "filing_date": "2024-01-31",
                "source_url": "https://www.sec.gov/example",
                "dataset_date": "2024-01-31",
                "run_id": "run-1",
            }
        ],
    )

    result = evaluate_quality(curated_path, CONTRACT_PATH, "run-1")

    assert result["status"] == "passed"
    assert result["failed_checks"] == []


def test_quality_gate_fails_when_required_ids_are_null(tmp_path: Path) -> None:
    curated_path = tmp_path / "curated-records.jsonl"
    _write_json_lines(
        curated_path,
        [
            {
                "accession_number": "",
                "company_cik": "123456",
                "company_name": "Example Holdings Inc",
                "form_type": "10-K",
                "filing_date": "2024-01-31",
                "source_url": "https://www.sec.gov/example",
                "dataset_date": "2024-01-31",
                "run_id": "run-1",
            }
        ],
    )

    result = evaluate_quality(curated_path, CONTRACT_PATH, "run-1")

    assert result["status"] == "failed"
    assert "required_ids_non_null" in result["failed_checks"]
