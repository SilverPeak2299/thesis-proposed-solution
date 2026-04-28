"""Shared storage path helpers for local and object-style outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from thesis_proposed_solution.runtime_config import GoldTableConfig, ObjectStorageConfig


@dataclass(frozen=True)
class ObjectStorageTarget:
    bucket: str
    key: str
    local_path: Path

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


def normalize_prefix(prefix: str) -> str:
    return prefix.strip("/")


def _build_object_target(
    *,
    base_dir: Path,
    bucket: str,
    prefix: str,
    parts: list[str],
) -> ObjectStorageTarget:
    normalized_prefix = normalize_prefix(prefix)
    key_parts = [part.strip("/") for part in [normalized_prefix, *parts] if part]
    key = "/".join(key_parts)
    local_path = base_dir / bucket
    for part in key_parts:
        local_path = local_path / part
    return ObjectStorageTarget(bucket=bucket, key=key, local_path=local_path)


def build_raw_payload_target(
    config: ObjectStorageConfig,
    *,
    dataset_date: str,
    run_id: str,
) -> ObjectStorageTarget:
    return _build_object_target(
        base_dir=config.local_base_dir,
        bucket=config.raw_bucket,
        prefix=config.raw_prefix,
        parts=[f"dataset_date={dataset_date}", f"run_id={run_id}", "payload.json"],
    )


def build_raw_records_target(
    config: ObjectStorageConfig,
    *,
    dataset_date: str,
    run_id: str,
) -> ObjectStorageTarget:
    return _build_object_target(
        base_dir=config.local_base_dir,
        bucket=config.raw_bucket,
        prefix=config.raw_prefix,
        parts=[f"dataset_date={dataset_date}", f"run_id={run_id}", "normalized-records.jsonl"],
    )


def build_curated_target(
    config: ObjectStorageConfig,
    *,
    dataset_date: str,
    run_id: str,
) -> ObjectStorageTarget:
    return _build_object_target(
        base_dir=config.local_base_dir,
        bucket=config.curated_bucket,
        prefix=config.curated_prefix,
        parts=[f"dataset_date={dataset_date}", f"run_id={run_id}", "curated-records.jsonl"],
    )


def build_manifest_target(
    config: ObjectStorageConfig,
    *,
    pipeline_id: str,
    dataset_date: str,
    run_id: str,
) -> ObjectStorageTarget:
    return _build_object_target(
        base_dir=config.local_base_dir,
        bucket=config.manifest_bucket,
        prefix=config.manifest_prefix,
        parts=[pipeline_id, f"dataset_date={dataset_date}", f"run_id={run_id}", "run-manifest.json"],
    )


def build_gold_table_directory(
    config: GoldTableConfig,
    *,
    dataset_date: str,
    dataset_version: str,
) -> Path:
    return (
        config.local_tables_dir
        / config.gold_table_bucket
        / config.gold_namespace
        / config.gold_table
        / f"dataset_date={dataset_date}"
        / f"dataset_version={dataset_version}"
    )


def build_gold_table_uri(config: GoldTableConfig) -> str:
    return (
        f"s3tables://{config.gold_table_bucket}/"
        f"{config.gold_namespace}/{config.gold_table}"
    )
