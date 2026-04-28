from __future__ import annotations

from thesis_proposed_solution.manifests import (
    create_initial_manifest,
    finalize_manifest,
    record_ingest_outputs,
    record_promotion_result,
    record_quality_result,
    record_transform_outputs,
    validate_manifest,
)


def test_manifest_generation_captures_required_governance_fields() -> None:
    manifest = create_initial_manifest(
        run_id="run-1",
        pipeline_id="edgar_governed_pipeline",
        dataset_date="2024-01-31",
        source_ref="file:///tmp/source.json",
        release_manifest_ref="release.json",
        terraform_state_ref="tfstate/1",
        change_ref="issue/1",
        gold_table_bucket="gold-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        job_refs={"ingest": "jobs/ingest/edgar_ingest.py"},
    )
    manifest = record_ingest_outputs(
        manifest,
        {
            "raw_payload_uri": "s3://raw/payload.json",
            "raw_payload_path": "/tmp/raw/payload.json",
            "raw_records_uri": "s3://raw/normalized-records.jsonl",
            "raw_records_path": "/tmp/raw/normalized-records.jsonl",
            "row_count": 2,
        },
    )
    manifest = record_transform_outputs(
        manifest,
        {
            "curated_uri": "s3://curated/curated-records.jsonl",
            "curated_path": "/tmp/curated/curated-records.jsonl",
            "contract_path": "/tmp/contract.json",
            "row_count": 2,
        },
    )
    manifest = record_quality_result(
        manifest,
        {
            "run_id": "run-1",
            "checks": [],
            "failed_checks": [],
            "status": "passed",
        },
    )
    manifest = record_promotion_result(
        manifest,
        {
            "dataset_version": "deadbeef12345678",
            "gold_write_result": {"table_uri": "s3tables://gold-bucket/edgar/filings"},
            "row_count": 2,
        },
    )
    manifest = finalize_manifest(manifest, "succeeded")

    assert manifest["gold_table_bucket"] == "gold-bucket"
    assert manifest["gold_namespace"] == "edgar"
    assert manifest["gold_table"] == "filings"
    assert manifest["dataset_version"] == "deadbeef12345678"
    assert validate_manifest(manifest) == []
