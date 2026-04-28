from __future__ import annotations

from pathlib import Path

from thesis_proposed_solution.contracts import (
    coerce_record_to_contract,
    load_contract,
    records_match_contract,
    required_fields_populated,
)

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "edgar_curated_contract.json"


def test_contract_helpers_coerce_and_validate_records() -> None:
    contract = load_contract(CONTRACT_PATH)
    record = coerce_record_to_contract(
        {
            "accession_number": 123,
            "company_cik": 456,
            "company_name": "Example Holdings Inc",
            "form_type": "10-K",
            "filing_date": "2024-01-31",
            "source_url": "https://www.sec.gov/example",
            "dataset_date": "2024-01-31",
            "run_id": "run-1",
        },
        contract,
    )

    schema_matches, schema_errors = records_match_contract([record], contract)
    required_matches, required_errors = required_fields_populated([record], contract)

    assert record["accession_number"] == "123"
    assert schema_matches is True
    assert schema_errors == []
    assert required_matches is True
    assert required_errors == []
