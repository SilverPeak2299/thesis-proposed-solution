from __future__ import annotations

from pathlib import Path

from scripts.run_local_etl import run_pipeline
from thesis_proposed_solution.runtime_config import (
    GoldTableConfig,
    GovernanceRefs,
    ObjectStorageConfig,
    PipelineRuntimeConfig,
)


def test_local_governed_flow_produces_manifest_and_gold_table_coordinates(tmp_path: Path) -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "edgar_sample" / "submissions.json"
    config = PipelineRuntimeConfig(
        pipeline_id="edgar_governed_pipeline",
        dataset_date="2024-01-31",
        source_uri=str(fixture_path),
        object_storage=ObjectStorageConfig(
            raw_bucket="raw-bucket",
            raw_prefix="edgar/raw",
            curated_bucket="curated-bucket",
            curated_prefix="edgar/curated",
            manifest_bucket="manifest-bucket",
            manifest_prefix="governed-runs",
            local_base_dir=tmp_path / "object-storage",
        ),
        gold_table=GoldTableConfig(
            gold_table_bucket="gold-bucket",
            gold_namespace="edgar",
            gold_table="filings",
            local_tables_dir=tmp_path / "s3-tables",
        ),
        governance=GovernanceRefs(
            release_manifest_ref="release-manifests/dev-edgar-v1.json",
            terraform_state_ref="terraform-state/dev/serial-0001",
            change_ref="issue/EDGAR-1",
        ),
    )

    manifest = run_pipeline(config, run_id="integration-run")

    assert Path(manifest["raw_outputs"]["payload_path"]).exists()
    assert Path(manifest["raw_outputs"]["normalized_path"]).exists()
    assert Path(manifest["curated_outputs"]["curated_path"]).exists()
    assert Path(manifest["gold_write_result"]["records_path"]).exists()
    assert manifest["gold_table_bucket"] == "gold-bucket"
    assert manifest["gold_namespace"] == "edgar"
    assert manifest["gold_table"] == "filings"
    assert manifest["dataset_version"]
    assert manifest["status"] == "succeeded"


def test_replayed_runs_keep_the_same_dataset_version_for_identical_inputs(tmp_path: Path) -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "edgar_sample" / "submissions.json"
    config = PipelineRuntimeConfig(
        pipeline_id="edgar_governed_pipeline",
        dataset_date="2024-01-31",
        source_uri=str(fixture_path),
        object_storage=ObjectStorageConfig(
            raw_bucket="raw-bucket",
            raw_prefix="edgar/raw",
            curated_bucket="curated-bucket",
            curated_prefix="edgar/curated",
            manifest_bucket="manifest-bucket",
            manifest_prefix="governed-runs",
            local_base_dir=tmp_path / "object-storage",
        ),
        gold_table=GoldTableConfig(
            gold_table_bucket="gold-bucket",
            gold_namespace="edgar",
            gold_table="filings",
            local_tables_dir=tmp_path / "s3-tables",
        ),
        governance=GovernanceRefs(
            release_manifest_ref="release-manifests/dev-edgar-v1.json",
            terraform_state_ref="terraform-state/dev/serial-0001",
            change_ref="issue/EDGAR-1",
        ),
    )

    first_manifest = run_pipeline(config, run_id="integration-run-1")
    second_manifest = run_pipeline(config, run_id="integration-run-2")

    assert first_manifest["dataset_version"] == second_manifest["dataset_version"]
