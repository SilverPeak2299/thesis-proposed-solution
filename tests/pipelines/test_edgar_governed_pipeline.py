from __future__ import annotations

from pathlib import Path

from pipelines.edgar_governed_pipeline import (
    build_final_manifest,
    build_pipeline_spec,
    build_run_context,
    dependency_map,
    select_quality_branch,
)


def test_pipeline_spec_has_expected_task_order_and_dependencies() -> None:
    spec = build_pipeline_spec()
    dependencies = dependency_map(spec)

    assert [task.task_id for task in spec] == [
        "initialize_run_context",
        "ingest_edgar_slice",
        "transform_curated_dataset",
        "evaluate_curated_quality",
        "branch_on_quality_result",
        "promote_to_gold_table",
        "finalize_manifest_status",
    ]
    assert dependencies["ingest_edgar_slice"] == ("initialize_run_context",)
    assert dependencies["transform_curated_dataset"] == ("ingest_edgar_slice",)
    assert dependencies["evaluate_curated_quality"] == ("transform_curated_dataset",)
    assert dependencies["branch_on_quality_result"] == ("evaluate_curated_quality",)
    assert dependencies["promote_to_gold_table"] == ("branch_on_quality_result",)
    assert dependencies["finalize_manifest_status"] == (
        "branch_on_quality_result",
        "promote_to_gold_table",
    )


def test_quality_branch_blocks_promotion_when_quality_fails() -> None:
    assert select_quality_branch({"status": "passed"}) == "promote_to_gold_table"
    assert select_quality_branch({"status": "failed"}) == "finalize_manifest_status"


def test_run_context_and_finalizer_write_manifest_for_dag_path(tmp_path: Path) -> None:
    release_manifest = tmp_path / "release.json"
    terraform_state = tmp_path / "terraform-state.json"
    change_record = tmp_path / "change.json"
    release_manifest.write_text("{}", encoding="utf-8")
    terraform_state.write_text("{}", encoding="utf-8")
    change_record.write_text("{}", encoding="utf-8")

    conf = {
        "dataset_date": "2024-01-31",
        "source_uri": "file:///tmp/source.json",
        "raw_bucket": "raw-bucket",
        "raw_prefix": "edgar/raw",
        "curated_bucket": "curated-bucket",
        "curated_prefix": "edgar/curated",
        "manifest_bucket": "manifest-bucket",
        "manifest_prefix": "governed-runs",
        "release_manifest_ref": str(release_manifest),
        "terraform_state_ref": str(terraform_state),
        "change_ref": str(change_record),
        "gold_table_bucket": "gold-bucket",
        "gold_namespace": "edgar",
        "gold_table": "filings",
        "storage_mode": "local",
        "local_base_dir": str(tmp_path / "object-storage"),
    }

    run_context = build_run_context(conf, run_id="dag-run-1")
    manifest = build_final_manifest(
        conf,
        run_context,
        ingest_summary={
            "raw_payload_uri": "s3://raw-bucket/edgar/raw/payload.json",
            "raw_payload_path": str(tmp_path / "payload.json"),
            "raw_records_uri": "s3://raw-bucket/edgar/raw/normalized-records.jsonl",
            "raw_records_path": str(tmp_path / "normalized-records.jsonl"),
            "row_count": 2,
        },
        transform_summary={
            "curated_uri": "s3://curated-bucket/edgar/curated/curated-records.jsonl",
            "curated_path": str(tmp_path / "curated-records.jsonl"),
            "contract_path": "/tmp/contract.json",
            "row_count": 2,
        },
        quality_summary={
            "run_id": "dag-run-1",
            "checks": [],
            "failed_checks": [],
            "status": "passed",
            "row_count": 2,
        },
        promotion_summary={
            "dataset_version": "deadbeef12345678",
            "gold_write_result": {
                "table_uri": "s3tables://gold-bucket/edgar/filings",
                "row_count": 2,
            },
            "row_count": 2,
        },
    )

    assert manifest["status"] == "succeeded"
    assert manifest["manifest_path"] is not None
    assert Path(manifest["manifest_path"]).exists()
    assert manifest["metadata_refs"]["openlineage_event_path"] is not None
    assert Path(manifest["metadata_refs"]["openlineage_event_path"]).exists()
