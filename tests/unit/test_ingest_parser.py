from __future__ import annotations

from jobs.ingest.edgar_ingest import _extract_records, _normalize_record


def test_ingest_supports_sec_recent_parallel_arrays() -> None:
    payload = {
        "cik": "320193",
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-24-000123", "0000320193-24-000124"],
                "filingDate": ["2024-01-31", "2024-02-01"],
                "form": ["10-Q", "8-K"],
                "primaryDocument": ["a10q.htm", "a8k.htm"],
            }
        },
    }

    records = _extract_records(payload)
    normalized = [_normalize_record(record, payload) for record in records]

    assert len(records) == 2
    assert normalized[0]["company_cik"] == "320193"
    assert normalized[0]["company_name"] == "Apple Inc."
    assert normalized[0]["form_type"] == "10-Q"
    assert normalized[0]["source_url"] == "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/a10q.htm"
