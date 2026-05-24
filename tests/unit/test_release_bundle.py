from __future__ import annotations

import json
from pathlib import Path

from scripts.build_release_bundle import main


def test_build_release_bundle_writes_governance_files(tmp_path: Path) -> None:
    artifact_bundle = tmp_path / "governed-release-bundle.zip"
    artifact_bundle.write_bytes(b"bundle-bytes")
    attestation_bundle = tmp_path / "governed-release-attestation.json"
    attestation_bundle.write_text('{"bundle":true}', encoding="utf-8")

    release_manifest = tmp_path / "release-manifests" / "release-main-deadbeef.json"
    change_record = tmp_path / "changes" / "release-main-deadbeef.json"
    runtime_config = tmp_path / "runtime-configs" / "release-main-deadbeef.json"
    summary_path = tmp_path / "build" / "release-governance-summary.json"

    exit_code = main(
        [
            "--release-manifest-output",
            str(release_manifest),
            "--change-output",
            str(change_record),
            "--runtime-config-output",
            str(runtime_config),
            "--summary-output",
            str(summary_path),
            "--release-id",
            "release-main-deadbeef",
            "--change-id",
            "release-main-deadbeef",
            "--artifact-bundle-path",
            str(artifact_bundle),
            "--artifact-bundle-sha256",
            "abc123",
            "--artifact-attestation-bundle-path",
            str(attestation_bundle),
            "--attestation-id",
            "77",
            "--attestation-url",
            "https://github.com/example/repo/attestations/77",
            "--subject-digest",
            "sha256:abc123",
            "--github-server-url",
            "https://github.com",
            "--github-repository",
            "example/repo",
            "--github-sha",
            "deadbeefcafebabe",
            "--github-ref-name",
            "main",
            "--github-run-id",
            "101",
            "--github-run-attempt",
            "1",
            "--github-run-number",
            "12",
            "--github-workflow",
            "Release Controls",
            "--github-workflow-ref",
            "example/repo/.github/workflows/release-controls.yml@refs/heads/main",
        ]
    )

    assert exit_code == 0

    release_payload = json.loads(release_manifest.read_text(encoding="utf-8"))
    change_payload = json.loads(change_record.read_text(encoding="utf-8"))
    runtime_payload = json.loads(runtime_config.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert release_payload["attestation"]["attestation_ref"] == "gh://attestations/77"
    assert release_payload["source_control"]["git_commit_sha"] == "deadbeefcafebabe"
    assert change_payload["ci_run"]["github_run_id"] == "101"
    assert runtime_payload["governance"]["release_manifest_ref"].endswith("release-main-deadbeef.json")
    assert summary_payload["artifact_bundle"]["subject_digest"] == "sha256:abc123"
