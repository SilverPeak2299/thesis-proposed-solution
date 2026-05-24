"""Governance reference validation, provenance capture, and metadata publication helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from configparser import ConfigParser
from copy import deepcopy
from base64 import b64encode
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from thesis_proposed_solution.storage import build_s3_target_from_uri, target_exists

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_REFERENCE_FIELDS = (
    "release_manifest_ref",
    "terraform_state_ref",
    "change_ref",
)
DEFAULT_OPENLINEAGE_NAMESPACE = "thesis_local_airflow"
DEFAULT_OPENMETADATA_PIPELINE_HOST_PORT = "http://airflow:8080"
DEFAULT_OPENMETADATA_STORAGE_SERVICE_NAME = "thesis_local_object_storage"
DEFAULT_OPENMETADATA_STORAGE_SERVICE_DESCRIPTION = (
    "Local object storage service that models the raw, curated, and gold assets "
    "produced by the governed EDGAR development pipeline."
)


def metadata_root_from_local_base_dir(local_base_dir: Path) -> Path:
    return local_base_dir.parent / "metadata"


def _looks_like_materialized_reference(reference: str) -> bool:
    parsed = urlparse(reference)
    if parsed.scheme in {"s3", "file"}:
        return True
    return Path(reference).is_absolute() or reference.startswith(".") or "/" in reference or reference.endswith(".json")


def resolve_reference(reference: str, *, repository_root: Path = REPOSITORY_ROOT) -> str | None:
    parsed = urlparse(reference)
    if parsed.scheme == "s3":
        return reference
    if parsed.scheme == "file":
        return str(Path(parsed.path).resolve())
    if not _looks_like_materialized_reference(reference):
        return None
    candidate = Path(reference)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    return str(candidate.resolve())


def reference_exists(reference: str, *, repository_root: Path = REPOSITORY_ROOT) -> bool:
    parsed = urlparse(reference)
    if parsed.scheme == "s3":
        return target_exists(build_s3_target_from_uri(reference))
    if parsed.scheme == "file":
        return Path(parsed.path).exists()
    resolved = resolve_reference(reference, repository_root=repository_root)
    if resolved is None:
        return False
    return Path(resolved).exists()


def validate_governance_references(
    *,
    release_manifest_ref: str,
    terraform_state_ref: str,
    change_ref: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, dict[str, Any]]:
    references = {
        "release_manifest_ref": release_manifest_ref,
        "terraform_state_ref": terraform_state_ref,
        "change_ref": change_ref,
    }
    checks: dict[str, dict[str, Any]] = {}
    for field_name, reference in references.items():
        resolved = resolve_reference(reference, repository_root=repository_root)
        checks[field_name] = {
            "reference": reference,
            "resolved_ref": resolved,
            "exists": reference_exists(reference, repository_root=repository_root),
        }
    return checks


def missing_reference_errors(reference_checks: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for field_name in GOVERNANCE_REFERENCE_FIELDS:
        check = reference_checks.get(field_name)
        if check is None:
            errors.append(f"missing reference check: {field_name}")
            continue
        if not check.get("exists"):
            errors.append(f"unresolved governance reference: {field_name} -> {check.get('reference')}")
    return errors


def _write_json(output_path: Path, payload: dict[str, Any]) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(output_path)


def _openlineage_run_uuid(manifest: dict[str, Any]) -> str:
    return str(uuid5(NAMESPACE_URL, f"{manifest['pipeline_id']}:{manifest['run_id']}"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_git_command(*args: str, repository_root: Path = REPOSITORY_ROOT) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, PermissionError):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _resolve_git_dir(repository_root: Path) -> Path | None:
    git_entry = repository_root / ".git"
    if git_entry.is_dir():
        return git_entry
    if not git_entry.is_file():
        return None
    try:
        raw = git_entry.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    prefix = "gitdir:"
    if not raw.lower().startswith(prefix):
        return None
    git_dir = raw[len(prefix) :].strip()
    candidate = Path(git_dir)
    if not candidate.is_absolute():
        candidate = (repository_root / candidate).resolve()
    return candidate


def _read_git_head(repository_root: Path) -> tuple[str | None, str | None]:
    git_dir = _resolve_git_dir(repository_root)
    if git_dir is None:
        return None, None

    try:
        head_value = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None, None

    if head_value.startswith("ref:"):
        ref_name = head_value.split(":", 1)[1].strip()
        ref_path = git_dir / ref_name
        if ref_path.exists():
            try:
                return ref_name, ref_path.read_text(encoding="utf-8").strip() or None
            except OSError:
                return ref_name, None

        packed_refs_path = git_dir / "packed-refs"
        if packed_refs_path.exists():
            try:
                for line in packed_refs_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("#") or line.startswith("^") or not line.strip():
                        continue
                    sha, _, packed_ref = line.partition(" ")
                    if packed_ref.strip() == ref_name:
                        return ref_name, sha
            except OSError:
                return ref_name, None
        return ref_name, None

    return None, head_value or None


def _read_git_remote_url(repository_root: Path) -> str | None:
    git_dir = _resolve_git_dir(repository_root)
    if git_dir is None:
        return None
    config_path = git_dir / "config"
    if not config_path.exists():
        return None
    parser = ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
    except OSError:
        return None
    section = 'remote "origin"'
    if not parser.has_section(section):
        return None
    return parser.get(section, "url", fallback=None)


def _normalize_repository_url(repository_url: str | None) -> str | None:
    if not repository_url:
        return None
    if repository_url.startswith("git@github.com:"):
        repository_url = "https://github.com/" + repository_url.split(":", 1)[1]
    if repository_url.endswith(".git"):
        repository_url = repository_url[:-4]
    return repository_url.rstrip("/")


def _commit_url(repository_url: str | None, commit_sha: str | None) -> str | None:
    normalized = _normalize_repository_url(repository_url)
    if not normalized or not commit_sha:
        return None
    if normalized.startswith("https://github.com/"):
        return f"{normalized}/commit/{commit_sha}"
    return None


def capture_source_control_provenance(*, repository_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    head_ref, head_commit = _read_git_head(repository_root)
    commit_sha = _run_git_command("rev-parse", "HEAD", repository_root=repository_root) or head_commit
    branch = _run_git_command("branch", "--show-current", repository_root=repository_root)
    if branch is None and head_ref is not None and head_ref.startswith("refs/heads/"):
        branch = head_ref[len("refs/heads/") :]
    repository_url = _normalize_repository_url(
        _run_git_command("remote", "get-url", "origin", repository_root=repository_root)
        or _read_git_remote_url(repository_root)
    )
    dirty_output = _run_git_command("status", "--short", "--untracked-files=no", repository_root=repository_root)
    return {
        "git_commit_sha": commit_sha,
        "git_branch": branch,
        "repository_url": repository_url,
        "commit_url": _commit_url(repository_url, commit_sha),
        "git_worktree_dirty": bool(dirty_output) if dirty_output is not None else None,
        "repository_root": str(repository_root),
    }


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _load_reference_payload(
    reference: str | None,
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any] | None:
    if not reference:
        return None
    resolved = resolve_reference(reference, repository_root=repository_root)
    if resolved is None:
        return None
    path = Path(resolved)
    if not path.exists():
        return None
    return _load_json_file(path)


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def capture_code_bundle_provenance(
    *,
    job_refs: dict[str, str],
    release_manifest_ref: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    release_manifest_path = resolve_reference(release_manifest_ref, repository_root=repository_root)
    release_manifest_payload = (
        _load_json_file(Path(release_manifest_path))
        if release_manifest_path is not None and Path(release_manifest_path).exists()
        else None
    )

    artifact_paths: dict[str, str] = {}
    if release_manifest_payload is not None:
        dag_bundle_ref = release_manifest_payload.get("dag_bundle_ref")
        if isinstance(dag_bundle_ref, str) and dag_bundle_ref:
            artifact_paths["dag"] = dag_bundle_ref
        release_jobs = release_manifest_payload.get("jobs")
        if isinstance(release_jobs, dict):
            for role, path in release_jobs.items():
                if isinstance(path, str) and path:
                    artifact_paths[str(role)] = path

    for role, path in job_refs.items():
        artifact_paths.setdefault(role, path)

    artifacts: dict[str, dict[str, Any]] = {}
    for role, artifact_ref in artifact_paths.items():
        resolved = resolve_reference(artifact_ref, repository_root=repository_root)
        artifact_path = Path(resolved) if resolved is not None else None
        exists = artifact_path is not None and artifact_path.exists()
        artifacts[role] = {
            "path": artifact_ref,
            "resolved_ref": resolved,
            "exists": exists,
            "sha256": _sha256_file(artifact_path) if exists else None,
        }

    release_manifest_digest = None
    if release_manifest_path is not None and Path(release_manifest_path).exists():
        release_manifest_digest = _sha256_file(Path(release_manifest_path))

    return {
        "release_manifest_ref": release_manifest_ref,
        "release_manifest_sha256": release_manifest_digest,
        "artifact_bundle": (
            deepcopy(release_manifest_payload.get("artifact_bundle"))
            if isinstance(release_manifest_payload, dict)
            and isinstance(release_manifest_payload.get("artifact_bundle"), dict)
            else None
        ),
        "artifacts": artifacts,
    }


def capture_attestation_provenance(
    source_control: dict[str, Any],
    *,
    release_manifest_payload: dict[str, Any] | None = None,
    change_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    release_attestation = (
        release_manifest_payload.get("attestation")
        if isinstance(release_manifest_payload, dict)
        and isinstance(release_manifest_payload.get("attestation"), dict)
        else {}
    )
    change_attestation = (
        change_payload.get("attestation")
        if isinstance(change_payload, dict)
        and isinstance(change_payload.get("attestation"), dict)
        else {}
    )
    github_run_id = os.getenv("GITHUB_RUN_ID")
    github_repository = os.getenv("GITHUB_REPOSITORY")
    github_server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    github_run_url = None
    if github_run_id and github_repository:
        github_run_url = f"{github_server_url.rstrip('/')}/{github_repository}/actions/runs/{github_run_id}"

    attestation_ref = _first_non_empty(
        os.getenv("GITHUB_ATTESTATION_REF"),
        os.getenv("GITHUB_BUILD_PROVENANCE_REF"),
        os.getenv("GITHUB_PROVENANCE_REF"),
        release_attestation.get("attestation_ref"),
        change_attestation.get("attestation_ref"),
    )
    attestation_url = _first_non_empty(
        os.getenv("GITHUB_ATTESTATION_URL"),
        release_attestation.get("attestation_url"),
        change_attestation.get("attestation_url"),
    )
    if attestation_url is None and isinstance(attestation_ref, str) and attestation_ref.startswith("http"):
        attestation_url = attestation_ref

    subject_digest = _first_non_empty(
        os.getenv("GITHUB_ATTESTATION_SUBJECT_DIGEST"),
        os.getenv("GITHUB_BUILD_PROVENANCE_SUBJECT_DIGEST"),
        release_attestation.get("subject_digest"),
        change_attestation.get("subject_digest"),
    )
    workflow_ref = _first_non_empty(
        os.getenv("GITHUB_WORKFLOW_REF"),
        release_attestation.get("github_workflow_ref"),
        change_attestation.get("github_workflow_ref"),
    )
    github_run_id = _first_non_empty(
        github_run_id,
        release_attestation.get("github_run_id"),
        change_attestation.get("github_run_id"),
    )
    github_repository = _first_non_empty(
        github_repository,
        release_attestation.get("github_repository"),
        change_attestation.get("github_repository"),
    )
    github_run_url = _first_non_empty(
        github_run_url,
        release_attestation.get("github_run_url"),
        change_attestation.get("github_run_url"),
    )
    if github_run_url is None and github_run_id and github_repository:
        github_run_url = f"{github_server_url.rstrip('/')}/{github_repository}/actions/runs/{github_run_id}"
    commit_sha = _first_non_empty(
        os.getenv("GITHUB_SHA"),
        source_control.get("git_commit_sha"),
        release_attestation.get("commit_sha"),
        change_attestation.get("commit_sha"),
    )

    return {
        "available": any(
            [
                attestation_ref,
                attestation_url,
                subject_digest,
                github_run_id,
                workflow_ref,
            ]
        ),
        "provider": "github",
        "github_repository": github_repository,
        "github_run_id": github_run_id,
        "github_run_url": github_run_url,
        "github_workflow_ref": workflow_ref,
        "attestation_ref": attestation_ref,
        "attestation_url": attestation_url,
        "subject_digest": subject_digest,
        "commit_sha": commit_sha,
    }


def capture_run_provenance(
    *,
    job_refs: dict[str, str],
    release_manifest_ref: str,
    change_ref: str | None = None,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, dict[str, Any]]:
    release_manifest_payload = _load_reference_payload(
        release_manifest_ref,
        repository_root=repository_root,
    )
    change_payload = _load_reference_payload(
        change_ref,
        repository_root=repository_root,
    )
    release_source_control = (
        release_manifest_payload.get("source_control")
        if isinstance(release_manifest_payload, dict)
        and isinstance(release_manifest_payload.get("source_control"), dict)
        else {}
    )
    change_source_control = (
        change_payload.get("source_control")
        if isinstance(change_payload, dict)
        and isinstance(change_payload.get("source_control"), dict)
        else {}
    )
    source_control = capture_source_control_provenance(repository_root=repository_root)
    source_control = {
        "git_commit_sha": _first_non_empty(
            source_control.get("git_commit_sha"),
            release_source_control.get("git_commit_sha"),
            change_source_control.get("git_commit_sha"),
        ),
        "git_branch": _first_non_empty(
            source_control.get("git_branch"),
            release_source_control.get("git_branch"),
            change_source_control.get("git_branch"),
        ),
        "repository_url": _first_non_empty(
            source_control.get("repository_url"),
            release_source_control.get("repository_url"),
            change_source_control.get("repository_url"),
        ),
        "commit_url": _first_non_empty(
            source_control.get("commit_url"),
            release_source_control.get("commit_url"),
            change_source_control.get("commit_url"),
        ),
        "git_worktree_dirty": _first_non_empty(
            source_control.get("git_worktree_dirty"),
            release_source_control.get("git_worktree_dirty"),
            change_source_control.get("git_worktree_dirty"),
        ),
        "repository_root": source_control.get("repository_root"),
    }
    if source_control["commit_url"] is None:
        source_control["commit_url"] = _commit_url(
            source_control.get("repository_url"),
            source_control.get("git_commit_sha"),
        )
    return {
        "source_control": source_control,
        "code_bundle": capture_code_bundle_provenance(
            job_refs=job_refs,
            release_manifest_ref=release_manifest_ref,
            repository_root=repository_root,
        ),
        "attestation": capture_attestation_provenance(
            source_control,
            release_manifest_payload=release_manifest_payload,
            change_payload=change_payload,
        ),
    }


def _openmetadata_run_record(manifest: dict[str, Any], manifest_ref: str) -> dict[str, Any]:
    return {
        "entity_type": "pipeline_run",
        "pipeline_id": manifest["pipeline_id"],
        "run_id": manifest["run_id"],
        "dataset_date": manifest["dataset_date"],
        "status": manifest["status"],
        "manifest_ref": manifest_ref,
        "dataset_version": manifest["dataset_version"],
        "quality_status": (manifest.get("quality_result") or {}).get("status"),
        "row_counts": manifest["row_counts"],
        "source_ref": manifest["source_ref"],
        "release_manifest_ref": manifest["release_manifest_ref"],
        "terraform_state_ref": manifest["terraform_state_ref"],
        "change_ref": manifest["change_ref"],
        "source_control": manifest.get("source_control") or {},
        "code_bundle": manifest.get("code_bundle") or {},
        "attestation": manifest.get("attestation") or {},
    }


def _openmetadata_dataset_record(manifest: dict[str, Any], manifest_ref: str) -> dict[str, Any]:
    gold_write_result = manifest["gold_write_result"] or {}
    return {
        "entity_type": "dataset",
        "dataset_version": manifest["dataset_version"],
        "dataset_date": manifest["dataset_date"],
        "gold_table_bucket": manifest["gold_table_bucket"],
        "gold_namespace": manifest["gold_namespace"],
        "gold_table": manifest["gold_table"],
        "table_uri": gold_write_result.get("table_uri"),
        "records_path": gold_write_result.get("records_path"),
        "write_result_path": gold_write_result.get("write_result_path"),
        "content_digest": gold_write_result.get("content_digest"),
        "row_count": gold_write_result.get("row_count"),
        "source_curated_uri": gold_write_result.get("source_curated_uri"),
        "manifest_ref": manifest_ref,
        "run_id": manifest["run_id"],
        "source_control": manifest.get("source_control") or {},
        "attestation": manifest.get("attestation") or {},
        "upstreams": [
            manifest["source_ref"],
            manifest["raw_outputs"].get("normalized_uri"),
            manifest["curated_outputs"].get("curated_uri"),
        ],
    }


def _audit_chain_record(manifest: dict[str, Any], manifest_ref: str) -> dict[str, Any]:
    return {
        "dataset_version": manifest["dataset_version"],
        "run_id": manifest["run_id"],
        "pipeline_id": manifest["pipeline_id"],
        "manifest_ref": manifest_ref,
        "release_manifest_ref": manifest["release_manifest_ref"],
        "terraform_state_ref": manifest["terraform_state_ref"],
        "change_ref": manifest["change_ref"],
        "source_ref": manifest["source_ref"],
        "gold_table_uri": (manifest["gold_write_result"] or {}).get("table_uri"),
        "quality_status": (manifest.get("quality_result") or {}).get("status"),
        "source_control": manifest.get("source_control") or {},
        "code_bundle": manifest.get("code_bundle") or {},
        "attestation": manifest.get("attestation") or {},
    }


def build_openlineage_event(
    manifest: dict[str, Any],
    manifest_ref: str,
    *,
    job_namespace: str = DEFAULT_OPENLINEAGE_NAMESPACE,
) -> dict[str, Any]:
    gold_write_result = manifest["gold_write_result"] or {}
    source_control = manifest.get("source_control") or {}
    attestation = manifest.get("attestation") or {}
    inputs = [
        {"namespace": "file", "name": manifest["source_ref"]},
        {"namespace": "s3", "name": manifest["raw_outputs"].get("normalized_uri")},
        {"namespace": "s3", "name": manifest["curated_outputs"].get("curated_uri")},
    ]
    outputs = [
        {"namespace": "manifest", "name": manifest_ref},
    ]
    if gold_write_result.get("table_uri"):
        outputs.append(
            {
                "namespace": "s3tables",
                "name": gold_write_result["table_uri"],
                "facets": {
                    "version": {
                        "_producer": "thesis-proposed-solution/local-metadata",
                        "_schemaURL": "https://openlineage.io/spec/1-0-0/OpenLineage.json#/definitions/OutputDataset",
                        "datasetVersion": manifest["dataset_version"],
                        "contentDigest": gold_write_result.get("content_digest"),
                        "recordsPath": gold_write_result.get("records_path"),
                    }
                },
            }
        )

    return {
        "eventType": "COMPLETE",
        "eventTime": manifest["completed_at"],
        "producer": "thesis-proposed-solution/local-metadata",
        "schemaURL": "https://openlineage.io/spec/1-0-0/OpenLineage.json#/definitions/RunEvent",
        "run": {
            "runId": _openlineage_run_uuid(manifest),
            "facets": {
                "governance": {
                    "_producer": "thesis-proposed-solution/local-metadata",
                    "_schemaURL": "https://example.local/facets/governance.json",
                    "releaseManifestRef": manifest["release_manifest_ref"],
                    "terraformStateRef": manifest["terraform_state_ref"],
                    "changeRef": manifest["change_ref"],
                    "manifestRef": manifest_ref,
                    "orchestratorRunId": manifest["run_id"],
                    "gitCommitSha": source_control.get("git_commit_sha"),
                    "gitBranch": source_control.get("git_branch"),
                    "repositoryUrl": source_control.get("repository_url"),
                    "commitUrl": source_control.get("commit_url"),
                    "attestationRef": attestation.get("attestation_ref"),
                    "attestationUrl": attestation.get("attestation_url"),
                    "attestationSubjectDigest": attestation.get("subject_digest"),
                    "githubRunUrl": attestation.get("github_run_url"),
                }
            },
        },
        "job": {
            "namespace": job_namespace,
            "name": manifest["pipeline_id"],
        },
        "inputs": [item for item in inputs if item["name"]],
        "outputs": [item for item in outputs if item["name"]],
    }


def _normalize_openmetadata_api_endpoint(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    if normalized.endswith("/api"):
        return normalized
    if normalized.endswith("/api/v1"):
        return normalized[: -len("/v1")]
    return f"{normalized}/api"


def resolve_openmetadata_config(
    *,
    openmetadata_api_endpoint: str | None = None,
    openmetadata_username: str | None = None,
    openmetadata_password: str | None = None,
) -> dict[str, str] | None:
    api_endpoint = openmetadata_api_endpoint or os.getenv("OPENMETADATA_API_ENDPOINT")
    username = openmetadata_username or os.getenv("OPENMETADATA_USERNAME")
    password = openmetadata_password or os.getenv("OPENMETADATA_PASSWORD")
    pipeline_service_name = os.getenv("OPENMETADATA_PIPELINE_SERVICE_NAME", DEFAULT_OPENLINEAGE_NAMESPACE)
    pipeline_service_host_port = os.getenv(
        "OPENMETADATA_PIPELINE_SERVICE_HOST_PORT",
        DEFAULT_OPENMETADATA_PIPELINE_HOST_PORT,
    )
    storage_service_name = os.getenv(
        "OPENMETADATA_STORAGE_SERVICE_NAME",
        DEFAULT_OPENMETADATA_STORAGE_SERVICE_NAME,
    )

    if not any([api_endpoint, username, password]):
        return None
    if not all([api_endpoint, username, password]):
        raise ValueError(
            "OpenMetadata configuration is partial; set OPENMETADATA_API_ENDPOINT, "
            "OPENMETADATA_USERNAME, and OPENMETADATA_PASSWORD together."
        )

    return {
        "api_endpoint": _normalize_openmetadata_api_endpoint(api_endpoint),
        "username": username,
        "password": password,
        "pipeline_service_name": pipeline_service_name,
        "pipeline_service_host_port": pipeline_service_host_port,
        "storage_service_name": storage_service_name,
    }


def _extract_token(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("accessToken", "access_token", "token", "jwtToken", "jwt_token", "id_token"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        for value in payload.values():
            token = _extract_token(value)
            if token:
                return token
    elif isinstance(payload, list):
        for item in payload:
            token = _extract_token(item)
            if token:
                return token
    return None


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: int,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(url, data=body, headers=request_headers, method="POST")
    with request.urlopen(http_request, timeout=timeout) as response:
        raw_body = response.read().decode("utf-8")
        decoded_body: Any = json.loads(raw_body) if raw_body else None
        return getattr(response, "status", 200), decoded_body


def _put_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: int,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(url, data=body, headers=request_headers, method="PUT")
    with request.urlopen(http_request, timeout=timeout) as response:
        raw_body = response.read().decode("utf-8")
        decoded_body: Any = json.loads(raw_body) if raw_body else None
        return getattr(response, "status", 200), decoded_body


def login_openmetadata(
    *,
    api_endpoint: str,
    username: str,
    password: str,
    timeout: int = 30,
) -> str:
    candidate_urls = [
        f"{api_endpoint}/v1/users/login",
        f"{api_endpoint}/users/login",
        f"{api_endpoint}/v1/login",
        f"{api_endpoint}/login",
    ]
    errors_seen: list[str] = []
    for candidate_url in candidate_urls:
        try:
            _, payload = _post_json(
                candidate_url,
                {"email": username, "password": b64encode(password.encode("utf-8")).decode("ascii")},
                timeout=timeout,
            )
        except error.HTTPError as exc:
            errors_seen.append(f"{candidate_url} -> HTTP {exc.code}")
            continue
        token = _extract_token(payload)
        if token:
            return token
        errors_seen.append(f"{candidate_url} -> token missing in response payload")

    raise RuntimeError(
        "Unable to authenticate to OpenMetadata. Tried login endpoints: "
        + "; ".join(errors_seen)
    )


def _sanitize_entity_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized.lower() or "asset"


def _asset_prefix(asset_uri: str | None) -> str | None:
    if not asset_uri:
        return None
    parsed = urlparse(asset_uri)
    if parsed.scheme in {"s3", "s3tables"}:
        return f"/{parsed.netloc}{parsed.path}"
    if parsed.scheme == "file":
        return parsed.path
    return asset_uri


def _container_specs_for_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    gold_write_result = manifest.get("gold_write_result") or {}
    return [
        {
            "key": "raw",
            "name": _sanitize_entity_name(f"{manifest['pipeline_id']}_raw"),
            "display_name": f"{manifest['pipeline_id']} raw records",
            "description": f"Raw normalized records for {manifest['pipeline_id']}.",
            "asset_uri": manifest["raw_outputs"].get("normalized_uri"),
        },
        {
            "key": "curated",
            "name": _sanitize_entity_name(f"{manifest['pipeline_id']}_curated"),
            "display_name": f"{manifest['pipeline_id']} curated records",
            "description": f"Curated records for {manifest['pipeline_id']}.",
            "asset_uri": manifest["curated_outputs"].get("curated_uri"),
        },
        {
            "key": "gold",
            "name": _sanitize_entity_name(f"{manifest['pipeline_id']}_gold_{manifest['gold_table']}"),
            "display_name": f"{manifest['pipeline_id']} gold {manifest['gold_table']}",
            "description": f"Promoted gold output for {manifest['pipeline_id']}.",
            "asset_uri": gold_write_result.get("table_uri"),
        },
    ]


def _entity_ref(entity_payload: dict[str, Any], entity_type: str) -> dict[str, Any]:
    return {
        "id": entity_payload["id"],
        "type": entity_type,
        "name": entity_payload.get("name"),
        "fullyQualifiedName": entity_payload.get("fullyQualifiedName"),
    }


def _put_lineage_edge(
    *,
    api_endpoint: str,
    token: str,
    from_entity: dict[str, Any],
    to_entity: dict[str, Any],
    timeout: int,
    description: str,
    pipeline_entity: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    lineage_details: dict[str, Any] = {}
    if pipeline_entity is not None:
        lineage_details["pipeline"] = {
            "id": pipeline_entity["id"],
            "type": "pipeline",
        }

    edge_payload: dict[str, Any] = {
        "edge": {
            "fromEntity": {
                "id": from_entity["id"],
                "type": from_entity["type"],
            },
            "toEntity": {
                "id": to_entity["id"],
                "type": to_entity["type"],
            },
            "description": description,
        }
    }
    if lineage_details:
        edge_payload["edge"]["lineageDetails"] = lineage_details

    return _put_json(
        f"{api_endpoint}/v1/lineage",
        edge_payload,
        timeout=timeout,
        headers={"Authorization": f"Bearer {token}"},
    )


def emit_openlineage_event_to_openmetadata(
    manifest: dict[str, Any],
    *,
    manifest_ref: str,
    api_endpoint: str,
    username: str,
    password: str,
    pipeline_service_name: str = DEFAULT_OPENLINEAGE_NAMESPACE,
    pipeline_service_host_port: str = DEFAULT_OPENMETADATA_PIPELINE_HOST_PORT,
    storage_service_name: str = DEFAULT_OPENMETADATA_STORAGE_SERVICE_NAME,
    timeout: int = 30,
) -> dict[str, Any]:
    token = login_openmetadata(
        api_endpoint=api_endpoint,
        username=username,
        password=password,
        timeout=timeout,
    )
    auth_headers = {"Authorization": f"Bearer {token}"}

    _, pipeline_service_payload = _put_json(
        f"{api_endpoint}/v1/services/pipelineServices",
        {
            "name": pipeline_service_name,
            "serviceType": "Airflow",
            "description": "Local Docker Airflow service used for OpenLineage development runs.",
            "connection": {
                "config": {
                    "type": "Airflow",
                    "hostPort": pipeline_service_host_port,
                    "connection": {"type": "Backend"},
                }
            },
        },
        timeout=timeout,
        headers=auth_headers,
    )
    _, pipeline_payload = _put_json(
        f"{api_endpoint}/v1/pipelines",
        {
            "name": manifest["pipeline_id"],
            "service": pipeline_service_name,
            "displayName": manifest["pipeline_id"],
            "description": "Governed EDGAR Airflow DAG for local development and lineage rehearsal.",
            "sourceUrl": pipeline_service_host_port,
        },
        timeout=timeout,
        headers=auth_headers,
    )
    _, storage_service_payload = _put_json(
        f"{api_endpoint}/v1/services/storageServices",
        {
            "name": storage_service_name,
            "serviceType": "CustomStorage",
            "displayName": storage_service_name,
            "description": DEFAULT_OPENMETADATA_STORAGE_SERVICE_DESCRIPTION,
            "connection": {
                "config": {
                    "type": "CustomStorage",
                }
            },
        },
        timeout=timeout,
        headers=auth_headers,
    )

    container_entities: dict[str, dict[str, Any]] = {}
    for spec in _container_specs_for_manifest(manifest):
        _, container_payload = _put_json(
            f"{api_endpoint}/v1/containers",
            {
                "name": spec["name"],
                "service": storage_service_name,
                "displayName": spec["display_name"],
                "description": f"{spec['description']} Asset URI: {spec['asset_uri']}.",
                "prefix": _asset_prefix(spec["asset_uri"]),
            },
            timeout=timeout,
            headers=auth_headers,
        )
        container_entities[spec["key"]] = _entity_ref(container_payload, "container")

    pipeline_entity = _entity_ref(pipeline_payload, "pipeline")

    _put_lineage_edge(
        api_endpoint=api_endpoint,
        token=token,
        from_entity=container_entities["raw"],
        to_entity=pipeline_entity,
        timeout=timeout,
        description="The governed EDGAR pipeline consumes raw normalized records.",
    )
    _put_lineage_edge(
        api_endpoint=api_endpoint,
        token=token,
        from_entity=pipeline_entity,
        to_entity=container_entities["curated"],
        timeout=timeout,
        description="The governed EDGAR pipeline materializes the curated dataset.",
    )
    _put_lineage_edge(
        api_endpoint=api_endpoint,
        token=token,
        from_entity=container_entities["curated"],
        to_entity=pipeline_entity,
        timeout=timeout,
        description="The governed EDGAR pipeline consumes the curated dataset for quality checks and promotion.",
    )
    _put_lineage_edge(
        api_endpoint=api_endpoint,
        token=token,
        from_entity=pipeline_entity,
        to_entity=container_entities["gold"],
        timeout=timeout,
        description="The governed EDGAR pipeline publishes the gold dataset.",
    )
    _put_lineage_edge(
        api_endpoint=api_endpoint,
        token=token,
        from_entity=container_entities["raw"],
        to_entity=container_entities["curated"],
        timeout=timeout,
        description="Raw records are transformed into curated records by the governed EDGAR pipeline.",
        pipeline_entity=pipeline_entity,
    )
    _put_lineage_edge(
        api_endpoint=api_endpoint,
        token=token,
        from_entity=container_entities["curated"],
        to_entity=container_entities["gold"],
        timeout=timeout,
        description="Curated records are promoted into the gold dataset by the governed EDGAR pipeline.",
        pipeline_entity=pipeline_entity,
    )

    lineage_api_url = f"{api_endpoint}/v1/openlineage/lineage"
    status_code, _ = _post_json(
        lineage_api_url,
        build_openlineage_event(
            manifest,
            manifest_ref,
            job_namespace=pipeline_service_name,
        ),
        timeout=timeout,
        headers=auth_headers,
    )
    return {
        "openmetadata_lineage_api_url": lineage_api_url,
        "openmetadata_lineage_status_code": status_code,
        "openmetadata_pipeline_service_name": pipeline_service_payload.get("fullyQualifiedName", pipeline_service_name),
        "openmetadata_pipeline_fqn": pipeline_payload.get("fullyQualifiedName", manifest["pipeline_id"]),
        "openmetadata_storage_service_name": storage_service_payload.get("fullyQualifiedName", storage_service_name),
        "openmetadata_raw_container_fqn": container_entities["raw"].get("fullyQualifiedName"),
        "openmetadata_curated_container_fqn": container_entities["curated"].get("fullyQualifiedName"),
        "openmetadata_gold_container_fqn": container_entities["gold"].get("fullyQualifiedName"),
        "openmetadata_lineage_edge_count": 6,
    }


def publish_metadata_artifacts(
    manifest: dict[str, Any],
    *,
    manifest_ref: str,
    local_base_dir: Path,
    openlineage_job_namespace: str = DEFAULT_OPENLINEAGE_NAMESPACE,
) -> dict[str, str | None]:
    metadata_root = metadata_root_from_local_base_dir(local_base_dir)
    run_dir = metadata_root / "openmetadata" / "runs" / manifest["pipeline_id"] / f"dataset_date={manifest['dataset_date']}" / f"run_id={manifest['run_id']}"
    lineage_dir = metadata_root / "openlineage" / "events" / manifest["pipeline_id"] / f"dataset_date={manifest['dataset_date']}" / f"run_id={manifest['run_id']}"

    refs: dict[str, str | None] = {
        "openmetadata_run_path": _write_json(run_dir / "run-record.json", _openmetadata_run_record(manifest, manifest_ref)),
        "openmetadata_dataset_path": None,
        "audit_chain_path": None,
        "openlineage_event_path": _write_json(
            lineage_dir / "complete.json",
            build_openlineage_event(
                manifest,
                manifest_ref,
                job_namespace=openlineage_job_namespace,
            ),
        ),
    }

    if manifest.get("dataset_version"):
        dataset_dir = (
            metadata_root
            / "openmetadata"
            / "datasets"
            / manifest["gold_table_bucket"]
            / manifest["gold_namespace"]
            / manifest["gold_table"]
            / f"dataset_version={manifest['dataset_version']}"
        )
        refs["openmetadata_dataset_path"] = _write_json(
            dataset_dir / "dataset-record.json",
            _openmetadata_dataset_record(manifest, manifest_ref),
        )
        refs["audit_chain_path"] = _write_json(
            metadata_root / "audit-chain" / f"{manifest['dataset_version']}.json",
            _audit_chain_record(manifest, manifest_ref),
        )

    return refs


def publish_run_metadata(
    manifest: dict[str, Any],
    *,
    manifest_ref: str,
    local_base_dir: Path,
    openmetadata_api_endpoint: str | None = None,
    openmetadata_username: str | None = None,
    openmetadata_password: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    openmetadata_config = resolve_openmetadata_config(
        openmetadata_api_endpoint=openmetadata_api_endpoint,
        openmetadata_username=openmetadata_username,
        openmetadata_password=openmetadata_password,
    )
    openlineage_job_namespace = (
        openmetadata_config["pipeline_service_name"]
        if openmetadata_config is not None
        else DEFAULT_OPENLINEAGE_NAMESPACE
    )
    refs: dict[str, Any] = publish_metadata_artifacts(
        manifest,
        manifest_ref=manifest_ref,
        local_base_dir=local_base_dir,
        openlineage_job_namespace=openlineage_job_namespace,
    )
    if openmetadata_config is not None:
        refs.update(
            emit_openlineage_event_to_openmetadata(
                manifest,
                manifest_ref=manifest_ref,
                api_endpoint=openmetadata_config["api_endpoint"],
                username=openmetadata_config["username"],
                password=openmetadata_config["password"],
                pipeline_service_name=openmetadata_config["pipeline_service_name"],
                pipeline_service_host_port=openmetadata_config["pipeline_service_host_port"],
                storage_service_name=openmetadata_config["storage_service_name"],
                timeout=timeout,
            )
        )
    return refs
