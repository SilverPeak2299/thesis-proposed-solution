from __future__ import annotations

from pathlib import Path

from thesis_proposed_solution.runtime_config import GoldTableConfig, ObjectStorageConfig
from thesis_proposed_solution.storage import (
    build_curated_target,
    build_gold_table_directory,
    build_manifest_target,
    build_raw_payload_target,
    build_raw_records_target,
)


def test_storage_targets_map_bucket_prefix_to_local_paths(tmp_path: Path) -> None:
    config = ObjectStorageConfig(
        raw_bucket="raw-bucket",
        raw_prefix="edgar/raw",
        curated_bucket="curated-bucket",
        curated_prefix="edgar/curated",
        manifest_bucket="manifest-bucket",
        manifest_prefix="governed-runs",
        local_base_dir=tmp_path,
        storage_mode="local",
    )

    payload = build_raw_payload_target(config, dataset_date="2024-01-31", run_id="run-1")
    records = build_raw_records_target(config, dataset_date="2024-01-31", run_id="run-1")
    curated = build_curated_target(config, dataset_date="2024-01-31", run_id="run-1")
    manifest = build_manifest_target(
        config,
        pipeline_id="edgar_governed_pipeline",
        dataset_date="2024-01-31",
        run_id="run-1",
    )

    assert payload.uri == "s3://raw-bucket/edgar/raw/dataset_date=2024-01-31/run_id=run-1/payload.json"
    assert records.local_path == tmp_path / "raw-bucket" / "edgar" / "raw" / "dataset_date=2024-01-31" / "run_id=run-1" / "normalized-records.jsonl"
    assert curated.uri.endswith("/curated-records.jsonl")
    assert manifest.local_path.name == "run-manifest.json"


def test_s3_storage_targets_keep_durable_uri_without_local_path(tmp_path: Path) -> None:
    config = ObjectStorageConfig(
        raw_bucket="raw-bucket",
        raw_prefix="edgar/raw",
        curated_bucket="curated-bucket",
        curated_prefix="edgar/curated",
        manifest_bucket="manifest-bucket",
        manifest_prefix="governed-runs",
        local_base_dir=tmp_path,
        storage_mode="s3",
    )

    target = build_raw_records_target(config, dataset_date="2024-01-31", run_id="run-1")

    assert target.uri == "s3://raw-bucket/edgar/raw/dataset_date=2024-01-31/run_id=run-1/normalized-records.jsonl"
    assert target.local_path is None


def test_gold_table_directory_uses_table_coordinates(tmp_path: Path) -> None:
    config = GoldTableConfig(
        gold_table_bucket="gold-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        local_tables_dir=tmp_path,
    )
    table_dir = build_gold_table_directory(
        config,
        dataset_date="2024-01-31",
        dataset_version="deadbeef1234",
    )

    assert table_dir == tmp_path / "gold-bucket" / "edgar" / "filings" / "dataset_date=2024-01-31" / "dataset_version=deadbeef1234"
