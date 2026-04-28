"""Shared storage path helpers for local and object-style outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from thesis_proposed_solution.runtime_config import GoldTableConfig, ObjectStorageConfig


@dataclass(frozen=True)
class ObjectStorageTarget:
    bucket: str
    key: str
    storage_mode: str
    local_path: Path | None = None

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"

    @property
    def location_hint(self) -> str:
        return str(self.local_path) if self.local_path is not None else self.uri


def normalize_prefix(prefix: str) -> str:
    return prefix.strip("/")


def _build_object_target(
    *,
    config: ObjectStorageConfig,
    bucket: str,
    prefix: str,
    parts: list[str],
) -> ObjectStorageTarget:
    normalized_prefix = normalize_prefix(prefix)
    key_parts = [part.strip("/") for part in [normalized_prefix, *parts] if part]
    key = "/".join(key_parts)
    local_path: Path | None = None
    if config.storage_mode == "local":
        local_path = config.local_base_dir / bucket
        for part in key_parts:
            local_path = local_path / part
    return ObjectStorageTarget(
        bucket=bucket,
        key=key,
        storage_mode=config.storage_mode,
        local_path=local_path,
    )


def build_raw_payload_target(
    config: ObjectStorageConfig,
    *,
    dataset_date: str,
    run_id: str,
) -> ObjectStorageTarget:
    return _build_object_target(
        config=config,
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
        config=config,
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
        config=config,
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
        config=config,
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


def build_s3_target_from_uri(uri: str) -> ObjectStorageTarget:
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Expected s3:// URI, received {uri!r}")
    return ObjectStorageTarget(
        bucket=parsed.netloc,
        key=parsed.path.lstrip("/"),
        storage_mode="s3",
        local_path=None,
    )


def _get_s3_client():
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - only exercised in AWS-backed runs
        raise RuntimeError("boto3 is required for s3 storage mode") from exc
    return boto3.client("s3")


def write_bytes_target(target: ObjectStorageTarget, payload: bytes, *, content_type: str) -> None:
    if target.storage_mode == "local":
        if target.local_path is None:
            raise ValueError("local storage targets require a local path")
        target.local_path.parent.mkdir(parents=True, exist_ok=True)
        target.local_path.write_bytes(payload)
        return
    client = _get_s3_client()
    client.put_object(Bucket=target.bucket, Key=target.key, Body=payload, ContentType=content_type)


def write_json_target(target: ObjectStorageTarget, payload: Any) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    write_bytes_target(target, serialized, content_type="application/json")


def write_json_lines_target(target: ObjectStorageTarget, records: list[dict[str, Any]]) -> None:
    lines = [json.dumps(record, sort_keys=False) for record in records]
    serialized = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    write_bytes_target(target, serialized, content_type="application/x-ndjson")


def read_text_target(target: ObjectStorageTarget) -> str:
    if target.storage_mode == "local":
        if target.local_path is None:
            raise ValueError("local storage targets require a local path")
        return target.local_path.read_text(encoding="utf-8")
    client = _get_s3_client()
    response = client.get_object(Bucket=target.bucket, Key=target.key)
    return response["Body"].read().decode("utf-8")


def read_json_target(target: ObjectStorageTarget) -> Any:
    return json.loads(read_text_target(target))


def read_json_lines_target(target: ObjectStorageTarget) -> list[dict[str, Any]]:
    text = read_text_target(target)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def target_exists(target: ObjectStorageTarget) -> bool:
    if target.storage_mode == "local":
        return target.local_path is not None and target.local_path.exists()
    client = _get_s3_client()
    try:
        client.head_object(Bucket=target.bucket, Key=target.key)
        return True
    except Exception as exc:  # pragma: no cover - only exercised in AWS-backed runs
        response = getattr(exc, "response", {})
        error_code = response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise
