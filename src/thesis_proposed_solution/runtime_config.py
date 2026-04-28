"""Runtime configuration models and loaders."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ObjectStorageConfig:
    raw_bucket: str
    raw_prefix: str
    curated_bucket: str
    curated_prefix: str
    manifest_bucket: str
    manifest_prefix: str
    local_base_dir: Path
    storage_mode: str = "local"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ObjectStorageConfig":
        return cls(
            raw_bucket=data["raw_bucket"],
            raw_prefix=data["raw_prefix"],
            curated_bucket=data["curated_bucket"],
            curated_prefix=data["curated_prefix"],
            manifest_bucket=data["manifest_bucket"],
            manifest_prefix=data["manifest_prefix"],
            local_base_dir=Path(data["local_base_dir"]),
            storage_mode=data.get("storage_mode", "local"),
        )


@dataclass(frozen=True)
class GoldTableConfig:
    gold_table_bucket: str
    gold_namespace: str
    gold_table: str
    local_tables_dir: Path

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "GoldTableConfig":
        return cls(
            gold_table_bucket=data["gold_table_bucket"],
            gold_namespace=data["gold_namespace"],
            gold_table=data["gold_table"],
            local_tables_dir=Path(data["local_tables_dir"]),
        )


@dataclass(frozen=True)
class GovernanceRefs:
    release_manifest_ref: str
    terraform_state_ref: str
    change_ref: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "GovernanceRefs":
        return cls(
            release_manifest_ref=data["release_manifest_ref"],
            terraform_state_ref=data["terraform_state_ref"],
            change_ref=data["change_ref"],
        )


@dataclass(frozen=True)
class PipelineRuntimeConfig:
    pipeline_id: str
    dataset_date: str
    source_uri: str
    object_storage: ObjectStorageConfig
    gold_table: GoldTableConfig
    governance: GovernanceRefs

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PipelineRuntimeConfig":
        return cls(
            pipeline_id=data["pipeline_id"],
            dataset_date=data["dataset_date"],
            source_uri=data["source_uri"],
            object_storage=ObjectStorageConfig.from_mapping(data["object_storage"]),
            gold_table=GoldTableConfig.from_mapping(data["gold_table"]),
            governance=GovernanceRefs.from_mapping(data["governance"]),
        )


def load_runtime_config(config_path: str | Path) -> PipelineRuntimeConfig:
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return PipelineRuntimeConfig.from_mapping(payload)


def runtime_config_to_dict(config: PipelineRuntimeConfig) -> dict[str, Any]:
    payload = asdict(config)
    payload["object_storage"]["local_base_dir"] = str(config.object_storage.local_base_dir)
    payload["gold_table"]["local_tables_dir"] = str(config.gold_table.local_tables_dir)
    return payload


def apply_runtime_overrides(
    config: PipelineRuntimeConfig,
    *,
    pipeline_id: str | None = None,
    dataset_date: str | None = None,
    source_uri: str | None = None,
    raw_bucket: str | None = None,
    raw_prefix: str | None = None,
    curated_bucket: str | None = None,
    curated_prefix: str | None = None,
    manifest_bucket: str | None = None,
    manifest_prefix: str | None = None,
    local_base_dir: str | Path | None = None,
    storage_mode: str | None = None,
    gold_table_bucket: str | None = None,
    gold_namespace: str | None = None,
    gold_table: str | None = None,
    local_tables_dir: str | Path | None = None,
    release_manifest_ref: str | None = None,
    terraform_state_ref: str | None = None,
    change_ref: str | None = None,
) -> PipelineRuntimeConfig:
    object_storage = replace(
        config.object_storage,
        raw_bucket=raw_bucket or config.object_storage.raw_bucket,
        raw_prefix=raw_prefix or config.object_storage.raw_prefix,
        curated_bucket=curated_bucket or config.object_storage.curated_bucket,
        curated_prefix=curated_prefix or config.object_storage.curated_prefix,
        manifest_bucket=manifest_bucket or config.object_storage.manifest_bucket,
        manifest_prefix=manifest_prefix or config.object_storage.manifest_prefix,
        local_base_dir=Path(local_base_dir)
        if local_base_dir is not None
        else config.object_storage.local_base_dir,
        storage_mode=storage_mode or config.object_storage.storage_mode,
    )
    gold_config = replace(
        config.gold_table,
        gold_table_bucket=gold_table_bucket or config.gold_table.gold_table_bucket,
        gold_namespace=gold_namespace or config.gold_table.gold_namespace,
        gold_table=gold_table or config.gold_table.gold_table,
        local_tables_dir=Path(local_tables_dir)
        if local_tables_dir is not None
        else config.gold_table.local_tables_dir,
    )
    governance = replace(
        config.governance,
        release_manifest_ref=release_manifest_ref or config.governance.release_manifest_ref,
        terraform_state_ref=terraform_state_ref or config.governance.terraform_state_ref,
        change_ref=change_ref or config.governance.change_ref,
    )
    return replace(
        config,
        pipeline_id=pipeline_id or config.pipeline_id,
        dataset_date=dataset_date or config.dataset_date,
        source_uri=source_uri or config.source_uri,
        object_storage=object_storage,
        gold_table=gold_config,
        governance=governance,
    )
