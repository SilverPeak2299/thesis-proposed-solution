"""Run manifest construction, persistence, and validation."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

REQUIRED_MANIFEST_FIELDS = [
    "run_id",
    "pipeline_id",
    "dataset_date",
    "source_ref",
    "release_manifest_ref",
    "terraform_state_ref",
    "change_ref",
    "job_refs",
    "raw_outputs",
    "curated_outputs",
    "gold_table_bucket",
    "gold_namespace",
    "gold_table",
    "dataset_version",
    "gold_write_result",
    "quality_result",
    "row_counts",
    "reference_checks",
    "source_control",
    "code_bundle",
    "attestation",
    "metadata_refs",
    "started_at",
    "completed_at",
    "status",
]


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def create_initial_manifest(
    *,
    run_id: str,
    pipeline_id: str,
    dataset_date: str,
    source_ref: str,
    release_manifest_ref: str,
    terraform_state_ref: str,
    change_ref: str,
    gold_table_bucket: str,
    gold_namespace: str,
    gold_table: str,
    job_refs: dict[str, str],
    source_control: dict[str, Any] | None = None,
    code_bundle: dict[str, Any] | None = None,
    attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "pipeline_id": pipeline_id,
        "dataset_date": dataset_date,
        "source_ref": source_ref,
        "release_manifest_ref": release_manifest_ref,
        "terraform_state_ref": terraform_state_ref,
        "change_ref": change_ref,
        "job_refs": deepcopy(job_refs),
        "raw_outputs": {},
        "curated_outputs": {},
        "gold_table_bucket": gold_table_bucket,
        "gold_namespace": gold_namespace,
        "gold_table": gold_table,
        "dataset_version": None,
        "gold_write_result": None,
        "quality_result": None,
        "row_counts": {},
        "reference_checks": {},
        "source_control": deepcopy(source_control or {"git_commit_sha": None, "git_branch": None, "repository_url": None}),
        "code_bundle": deepcopy(code_bundle or {"artifacts": {}}),
        "attestation": deepcopy(attestation or {"available": False}),
        "metadata_refs": {},
        "started_at": utc_now_iso(),
        "completed_at": None,
        "status": "running",
    }


def write_manifest(manifest: dict[str, Any], output_path: str | Path) -> None:
    output_ref = str(output_path)
    if output_ref.startswith("s3://"):
        from thesis_proposed_solution.storage import build_s3_target_from_uri, write_json_target

        write_json_target(build_s3_target_from_uri(output_ref), manifest)
        return

    local_path = Path(output_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with local_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def load_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest_ref = str(manifest_path)
    if manifest_ref.startswith("s3://"):
        from thesis_proposed_solution.storage import build_s3_target_from_uri, read_json_target

        payload = read_json_target(build_s3_target_from_uri(manifest_ref))
        if not isinstance(payload, dict):
            raise ValueError("Manifest payload must be a JSON object")
        return payload

    with Path(manifest_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def update_manifest(manifest: dict[str, Any], **updates: Any) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated.update(updates)
    return updated


def record_ingest_outputs(manifest: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated["raw_outputs"] = {
        "payload_uri": summary["raw_payload_uri"],
        "payload_path": summary["raw_payload_path"],
        "normalized_uri": summary["raw_records_uri"],
        "normalized_path": summary["raw_records_path"],
    }
    updated["row_counts"]["raw_records"] = summary["row_count"]
    return updated


def record_transform_outputs(manifest: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated["curated_outputs"] = {
        "curated_uri": summary["curated_uri"],
        "curated_path": summary["curated_path"],
        "contract_path": summary["contract_path"],
    }
    updated["row_counts"]["curated_records"] = summary["row_count"]
    return updated


def record_quality_result(manifest: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated["quality_result"] = deepcopy(summary)
    return updated


def record_promotion_result(manifest: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated["dataset_version"] = summary["dataset_version"]
    updated["gold_write_result"] = deepcopy(summary["gold_write_result"])
    updated["row_counts"]["promoted_records"] = summary["row_count"]
    return updated


def finalize_manifest(manifest: dict[str, Any], status: str) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated["status"] = status
    updated["completed_at"] = utc_now_iso()
    return updated


def record_reference_checks(manifest: dict[str, Any], reference_checks: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated["reference_checks"] = deepcopy(reference_checks)
    return updated


def record_metadata_refs(manifest: dict[str, Any], metadata_refs: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(manifest)
    updated["metadata_refs"] = deepcopy(metadata_refs)
    return updated


def compute_dataset_version(
    *,
    gold_table_bucket: str,
    gold_namespace: str,
    gold_table: str,
    write_result: dict[str, Any],
) -> str:
    payload = {
        "gold_table_bucket": gold_table_bucket,
        "gold_namespace": gold_namespace,
        "gold_table": gold_table,
        "write_result": write_result,
    }
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return digest[:16]


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in REQUIRED_MANIFEST_FIELDS:
        if field_name not in manifest:
            errors.append(f"missing field: {field_name}")

    for field_name in [
        "run_id",
        "pipeline_id",
        "dataset_date",
        "source_ref",
        "release_manifest_ref",
        "terraform_state_ref",
        "change_ref",
        "gold_table_bucket",
        "gold_namespace",
        "gold_table",
        "started_at",
        "status",
    ]:
        if not manifest.get(field_name):
            errors.append(f"empty field: {field_name}")

    quality_result = manifest.get("quality_result")
    if quality_result is None:
        errors.append("quality_result is required")

    reference_checks = manifest.get("reference_checks")
    if not isinstance(reference_checks, dict):
        errors.append("reference_checks must be a mapping")
    else:
        for field_name in ["release_manifest_ref", "terraform_state_ref", "change_ref"]:
            check = reference_checks.get(field_name)
            if check is None:
                errors.append(f"missing reference check: {field_name}")
            elif not check.get("exists"):
                errors.append(f"unresolved governance reference: {field_name}")

    for field_name in ["source_control", "code_bundle", "attestation"]:
        if not isinstance(manifest.get(field_name), dict):
            errors.append(f"{field_name} must be a mapping")

    if manifest.get("status") == "succeeded":
        if not manifest.get("dataset_version"):
            errors.append("dataset_version is required for successful runs")
        if not manifest.get("gold_write_result"):
            errors.append("gold_write_result is required for successful runs")
        metadata_refs = manifest.get("metadata_refs") or {}
        for field_name in [
            "openmetadata_run_path",
            "openmetadata_dataset_path",
            "audit_chain_path",
            "openlineage_event_path",
        ]:
            if not metadata_refs.get(field_name):
                errors.append(f"metadata ref is required for successful runs: {field_name}")

    if manifest.get("status") == "failed_quality" and manifest.get("dataset_version") is not None:
        errors.append("dataset_version must be null for failed quality runs")
    if manifest.get("status") == "failed_quality":
        metadata_refs = manifest.get("metadata_refs") or {}
        for field_name in ["openmetadata_run_path", "openlineage_event_path"]:
            if not metadata_refs.get(field_name):
                errors.append(f"metadata ref is required for failed quality runs: {field_name}")

    return errors
