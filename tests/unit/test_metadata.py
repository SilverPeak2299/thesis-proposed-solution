from __future__ import annotations

import json
from pathlib import Path

from thesis_proposed_solution.metadata import (
    missing_reference_errors,
    publish_metadata_artifacts,
    publish_run_metadata,
    validate_governance_references,
)


def test_validate_governance_references_requires_materialized_targets(tmp_path: Path) -> None:
    release_manifest = tmp_path / "release.json"
    terraform_state = tmp_path / "terraform-state.json"
    change_record = tmp_path / "change.json"
    release_manifest.write_text("{}", encoding="utf-8")
    terraform_state.write_text("{}", encoding="utf-8")
    change_record.write_text("{}", encoding="utf-8")

    checks = validate_governance_references(
        release_manifest_ref=str(release_manifest),
        terraform_state_ref=str(terraform_state),
        change_ref=str(change_record),
    )

    assert missing_reference_errors(checks) == []
    assert all(check["exists"] for check in checks.values())


def test_publish_metadata_artifacts_writes_openlineage_and_catalog_files(tmp_path: Path) -> None:
    manifest = {
        "run_id": "run-1",
        "pipeline_id": "edgar_governed_pipeline",
        "dataset_date": "2024-01-31",
        "source_ref": "/tmp/source.json",
        "release_manifest_ref": "release-manifests/local-dev.json",
        "terraform_state_ref": "terraform-state/local-docker-airflow.json",
        "change_ref": "changes/local-dev.json",
        "job_refs": {},
        "raw_outputs": {
            "normalized_uri": "s3://raw-bucket/edgar/raw/normalized-records.jsonl",
        },
        "curated_outputs": {
            "curated_uri": "s3://curated-bucket/edgar/curated/curated-records.jsonl",
        },
        "gold_table_bucket": "gold-bucket",
        "gold_namespace": "edgar",
        "gold_table": "filings",
        "dataset_version": "deadbeef12345678",
        "gold_write_result": {
            "table_uri": "s3tables://gold-bucket/edgar/filings",
            "records_path": "/tmp/records.jsonl",
            "write_result_path": "/tmp/write-result.json",
            "content_digest": "abc123",
            "row_count": 2,
            "source_curated_uri": "s3://curated-bucket/edgar/curated/curated-records.jsonl",
        },
        "quality_result": {"status": "passed"},
        "row_counts": {"raw_records": 2, "curated_records": 2, "promoted_records": 2},
        "reference_checks": {},
        "source_control": {
            "git_commit_sha": "abc123",
            "git_branch": "main",
            "repository_url": "https://github.com/example/repo",
            "commit_url": "https://github.com/example/repo/commit/abc123",
            "git_worktree_dirty": False,
        },
        "code_bundle": {
            "release_manifest_ref": "release-manifests/local-dev.json",
            "release_manifest_sha256": "deadbeef",
            "artifacts": {
                "dag": {
                    "path": "pipelines/edgar_governed_pipeline.py",
                    "resolved_ref": "/tmp/pipelines/edgar_governed_pipeline.py",
                    "exists": True,
                    "sha256": "feedface",
                }
            },
        },
        "attestation": {
            "available": True,
            "provider": "github",
            "attestation_ref": "gh://attestations/123",
            "attestation_url": "https://github.com/example/repo/attestations/123",
            "subject_digest": "sha256:abc123",
            "github_run_url": "https://github.com/example/repo/actions/runs/42",
        },
        "metadata_refs": {},
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:01:00+00:00",
        "status": "succeeded",
    }

    refs = publish_metadata_artifacts(
        manifest,
        manifest_ref="s3://manifest-bucket/governed-runs/run-manifest.json",
        local_base_dir=tmp_path / "object-storage",
    )

    assert Path(refs["openmetadata_run_path"]).exists()
    assert Path(refs["openmetadata_dataset_path"]).exists()
    assert Path(refs["audit_chain_path"]).exists()
    assert Path(refs["openlineage_event_path"]).exists()

    lineage_event = json.loads(Path(refs["openlineage_event_path"]).read_text(encoding="utf-8"))
    audit_chain = json.loads(Path(refs["audit_chain_path"]).read_text(encoding="utf-8"))
    assert lineage_event["eventType"] == "COMPLETE"
    assert lineage_event["run"]["runId"] == "cecd78ba-94f6-5629-8c68-eb94ebfd7869"
    assert lineage_event["run"]["facets"]["governance"]["orchestratorRunId"] == "run-1"
    assert audit_chain["source_control"]["git_commit_sha"] == "abc123"
    assert audit_chain["attestation"]["attestation_ref"] == "gh://attestations/123"


def test_publish_run_metadata_posts_openlineage_to_openmetadata(monkeypatch, tmp_path: Path) -> None:
    manifest = {
        "run_id": "run-1",
        "pipeline_id": "edgar_governed_pipeline",
        "dataset_date": "2024-01-31",
        "source_ref": "/tmp/source.json",
        "release_manifest_ref": "release-manifests/local-dev.json",
        "terraform_state_ref": "terraform-state/local-docker-airflow.json",
        "change_ref": "changes/local-dev.json",
        "job_refs": {},
        "raw_outputs": {
            "normalized_uri": "s3://raw-bucket/edgar/raw/normalized-records.jsonl",
        },
        "curated_outputs": {
            "curated_uri": "s3://curated-bucket/edgar/curated/curated-records.jsonl",
        },
        "gold_table_bucket": "gold-bucket",
        "gold_namespace": "edgar",
        "gold_table": "filings",
        "dataset_version": "deadbeef12345678",
        "gold_write_result": {
            "table_uri": "s3tables://gold-bucket/edgar/filings",
            "records_path": "/tmp/records.jsonl",
            "write_result_path": "/tmp/write-result.json",
            "content_digest": "abc123",
            "row_count": 2,
            "source_curated_uri": "s3://curated-bucket/edgar/curated/curated-records.jsonl",
        },
        "quality_result": {"status": "passed"},
        "row_counts": {"raw_records": 2, "curated_records": 2, "promoted_records": 2},
        "reference_checks": {},
        "source_control": {
            "git_commit_sha": "abc123",
            "git_branch": "main",
            "repository_url": "https://github.com/example/repo",
            "commit_url": "https://github.com/example/repo/commit/abc123",
            "git_worktree_dirty": False,
        },
        "code_bundle": {
            "release_manifest_ref": "release-manifests/local-dev.json",
            "release_manifest_sha256": "deadbeef",
            "artifacts": {},
        },
        "attestation": {
            "available": False,
            "provider": "github",
        },
        "metadata_refs": {},
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:01:00+00:00",
        "status": "succeeded",
    }
    observed_requests: list[dict[str, object]] = []

    class FakeResponse:
        def __init__(self, status: int, payload: dict[str, object] | None) -> None:
            self.status = status
            self._payload = payload
            self.headers = {}

        def read(self) -> bytes:
            if self._payload is None:
                return b""
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def fake_urlopen(http_request, timeout: int = 30):
        observed_requests.append(
            {
                "url": http_request.full_url,
                "headers": dict(http_request.header_items()),
                "body": json.loads(http_request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        if http_request.full_url.endswith("/v1/users/login"):
            return FakeResponse(200, {"accessToken": "jwt-token"})
        if http_request.full_url.endswith("/v1/services/pipelineServices"):
            return FakeResponse(200, {"id": "svc-pipeline", "name": "thesis_local_airflow", "fullyQualifiedName": "thesis_local_airflow"})
        if http_request.full_url.endswith("/v1/pipelines"):
            return FakeResponse(200, {"id": "pipeline-1", "name": "edgar_governed_pipeline", "fullyQualifiedName": "thesis_local_airflow.edgar_governed_pipeline"})
        if http_request.full_url.endswith("/v1/services/storageServices"):
            return FakeResponse(200, {"id": "svc-storage", "name": "thesis_local_object_storage", "fullyQualifiedName": "thesis_local_object_storage"})
        if http_request.full_url.endswith("/v1/containers"):
            container_name = json.loads(http_request.data.decode("utf-8"))["name"]
            return FakeResponse(200, {"id": f"{container_name}-id", "name": container_name, "fullyQualifiedName": f"thesis_local_object_storage.{container_name}"})
        if http_request.full_url.endswith("/v1/lineage"):
            return FakeResponse(200, {"status": "ok"})
        if http_request.full_url.endswith("/v1/openlineage/lineage"):
            return FakeResponse(201, {"status": "accepted"})
        raise AssertionError(f"Unexpected request URL: {http_request.full_url}")

    monkeypatch.setattr("thesis_proposed_solution.metadata.request.urlopen", fake_urlopen)

    refs = publish_run_metadata(
        manifest,
        manifest_ref="s3://manifest-bucket/governed-runs/run-manifest.json",
        local_base_dir=tmp_path / "object-storage",
        openmetadata_api_endpoint="http://openmetadata-server:8585/api",
        openmetadata_username="admin@open-metadata.org",
        openmetadata_password="admin",
    )

    assert refs["openmetadata_lineage_api_url"] == "http://openmetadata-server:8585/api/v1/openlineage/lineage"
    assert refs["openmetadata_lineage_status_code"] == 201
    assert refs["openmetadata_pipeline_fqn"] == "thesis_local_airflow.edgar_governed_pipeline"
    assert refs["openmetadata_gold_container_fqn"] == "thesis_local_object_storage.edgar_governed_pipeline_gold_filings"
    assert refs["openmetadata_lineage_edge_count"] == 6
    assert observed_requests[0]["url"] == "http://openmetadata-server:8585/api/v1/users/login"
    assert observed_requests[1]["url"] == "http://openmetadata-server:8585/api/v1/services/pipelineServices"
    assert observed_requests[1]["headers"]["Authorization"] == "Bearer jwt-token"
    assert observed_requests[2]["url"] == "http://openmetadata-server:8585/api/v1/pipelines"
    assert observed_requests[3]["url"] == "http://openmetadata-server:8585/api/v1/services/storageServices"
    assert observed_requests[4]["url"] == "http://openmetadata-server:8585/api/v1/containers"
    assert observed_requests[-1]["body"]["eventType"] == "COMPLETE"
    assert observed_requests[-1]["body"]["job"]["namespace"] == "thesis_local_airflow"
