"""Run the governed EDGAR ETL flow locally using the same job entrypoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jobs.ingest.edgar_ingest import run_ingest
from jobs.promote.promote_to_s3_table import run_promotion
from jobs.quality.curated_quality_gate import run_quality_gate
from jobs.transform.edgar_transform import DEFAULT_CONTRACT_PATH, run_transform
from thesis_proposed_solution.manifests import (
    create_initial_manifest,
    finalize_manifest,
    record_metadata_refs,
    record_reference_checks,
    record_ingest_outputs,
    record_promotion_result,
    record_quality_result,
    record_transform_outputs,
    validate_manifest,
)
from thesis_proposed_solution.metadata import (
    capture_run_provenance,
    missing_reference_errors,
    publish_run_metadata,
    validate_governance_references,
)
from thesis_proposed_solution.runtime_config import (
    PipelineRuntimeConfig,
    apply_runtime_overrides,
    load_runtime_config,
)
from thesis_proposed_solution.storage import build_manifest_target, write_json_target

JOB_REFS = {
    "ingest": "jobs/ingest/edgar_ingest.py",
    "transform": "jobs/transform/edgar_transform.py",
    "quality": "jobs/quality/curated_quality_gate.py",
    "promote": "jobs/promote/promote_to_s3_table.py",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--dataset-date")
    parser.add_argument("--source-uri")
    parser.add_argument("--raw-bucket")
    parser.add_argument("--raw-prefix")
    parser.add_argument("--curated-bucket")
    parser.add_argument("--curated-prefix")
    parser.add_argument("--manifest-bucket")
    parser.add_argument("--manifest-prefix")
    parser.add_argument("--local-base-dir")
    parser.add_argument("--storage-mode")
    parser.add_argument("--gold-table-bucket")
    parser.add_argument("--gold-namespace")
    parser.add_argument("--gold-table")
    parser.add_argument("--local-tables-dir")
    parser.add_argument("--release-manifest-ref")
    parser.add_argument("--terraform-state-ref")
    parser.add_argument("--change-ref")
    parser.add_argument("--contract-path", default=DEFAULT_CONTRACT_PATH)
    return parser


def _namespace(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _build_config(args: argparse.Namespace) -> PipelineRuntimeConfig:
    base_config = load_runtime_config(args.config)
    return apply_runtime_overrides(
        base_config,
        dataset_date=args.dataset_date,
        source_uri=args.source_uri,
        raw_bucket=args.raw_bucket,
        raw_prefix=args.raw_prefix,
        curated_bucket=args.curated_bucket,
        curated_prefix=args.curated_prefix,
        manifest_bucket=args.manifest_bucket,
        manifest_prefix=args.manifest_prefix,
        local_base_dir=args.local_base_dir,
        storage_mode=args.storage_mode,
        gold_table_bucket=args.gold_table_bucket,
        gold_namespace=args.gold_namespace,
        gold_table=args.gold_table,
        local_tables_dir=args.local_tables_dir,
        release_manifest_ref=args.release_manifest_ref,
        terraform_state_ref=args.terraform_state_ref,
        change_ref=args.change_ref,
    )


def run_pipeline(config: PipelineRuntimeConfig, *, run_id: str | None = None, contract_path: str = DEFAULT_CONTRACT_PATH) -> dict:
    effective_run_id = run_id or f"run-{uuid4().hex[:12]}"
    reference_checks = validate_governance_references(
        release_manifest_ref=config.governance.release_manifest_ref,
        terraform_state_ref=config.governance.terraform_state_ref,
        change_ref=config.governance.change_ref,
    )
    reference_errors = missing_reference_errors(reference_checks)
    if reference_errors:
        raise ValueError(f"Governance references are invalid: {reference_errors}")
    manifest_target = build_manifest_target(
        config.object_storage,
        pipeline_id=config.pipeline_id,
        dataset_date=config.dataset_date,
        run_id=effective_run_id,
    )
    provenance = capture_run_provenance(
        job_refs=JOB_REFS,
        release_manifest_ref=config.governance.release_manifest_ref,
    )
    manifest = create_initial_manifest(
        run_id=effective_run_id,
        pipeline_id=config.pipeline_id,
        dataset_date=config.dataset_date,
        source_ref=config.source_uri,
        release_manifest_ref=config.governance.release_manifest_ref,
        terraform_state_ref=config.governance.terraform_state_ref,
        change_ref=config.governance.change_ref,
        gold_table_bucket=config.gold_table.gold_table_bucket,
        gold_namespace=config.gold_table.gold_namespace,
        gold_table=config.gold_table.gold_table,
        job_refs=JOB_REFS,
        source_control=provenance["source_control"],
        code_bundle=provenance["code_bundle"],
        attestation=provenance["attestation"],
    )
    manifest = record_reference_checks(manifest, reference_checks)
    write_json_target(manifest_target, manifest)

    ingest_summary = run_ingest(
        _namespace(
            run_id=effective_run_id,
            dataset_date=config.dataset_date,
            source_uri=config.source_uri,
            raw_bucket=config.object_storage.raw_bucket,
            raw_prefix=config.object_storage.raw_prefix,
            manifest_bucket=config.object_storage.manifest_bucket,
            manifest_prefix=config.object_storage.manifest_prefix,
            release_manifest_ref=config.governance.release_manifest_ref,
            terraform_state_ref=config.governance.terraform_state_ref,
            change_ref=config.governance.change_ref,
            local_base_dir=str(config.object_storage.local_base_dir),
            storage_mode=config.object_storage.storage_mode,
        )
    )
    manifest = record_ingest_outputs(manifest, ingest_summary)
    write_json_target(manifest_target, manifest)

    transform_summary = run_transform(
        _namespace(
            run_id=effective_run_id,
            dataset_date=config.dataset_date,
            raw_bucket=config.object_storage.raw_bucket,
            raw_prefix=config.object_storage.raw_prefix,
            curated_bucket=config.object_storage.curated_bucket,
            curated_prefix=config.object_storage.curated_prefix,
            manifest_bucket=config.object_storage.manifest_bucket,
            manifest_prefix=config.object_storage.manifest_prefix,
            release_manifest_ref=config.governance.release_manifest_ref,
            terraform_state_ref=config.governance.terraform_state_ref,
            change_ref=config.governance.change_ref,
            contract_path=contract_path,
            local_base_dir=str(config.object_storage.local_base_dir),
            storage_mode=config.object_storage.storage_mode,
        )
    )
    manifest = record_transform_outputs(manifest, transform_summary)
    write_json_target(manifest_target, manifest)

    quality_summary = run_quality_gate(
        _namespace(
            run_id=effective_run_id,
            dataset_date=config.dataset_date,
            curated_bucket=config.object_storage.curated_bucket,
            curated_prefix=config.object_storage.curated_prefix,
            manifest_bucket=config.object_storage.manifest_bucket,
            manifest_prefix=config.object_storage.manifest_prefix,
            release_manifest_ref=config.governance.release_manifest_ref,
            terraform_state_ref=config.governance.terraform_state_ref,
            change_ref=config.governance.change_ref,
            contract_path=contract_path,
            local_base_dir=str(config.object_storage.local_base_dir),
            storage_mode=config.object_storage.storage_mode,
        )
    )
    manifest = record_quality_result(manifest, quality_summary)
    write_json_target(manifest_target, manifest)

    if quality_summary["status"] == "passed":
        promotion_summary = run_promotion(
            _namespace(
                run_id=effective_run_id,
                dataset_date=config.dataset_date,
                curated_bucket=config.object_storage.curated_bucket,
                curated_prefix=config.object_storage.curated_prefix,
                manifest_bucket=config.object_storage.manifest_bucket,
                manifest_prefix=config.object_storage.manifest_prefix,
                gold_table_bucket=config.gold_table.gold_table_bucket,
                gold_namespace=config.gold_table.gold_namespace,
                gold_table=config.gold_table.gold_table,
                release_manifest_ref=config.governance.release_manifest_ref,
                terraform_state_ref=config.governance.terraform_state_ref,
                change_ref=config.governance.change_ref,
                local_base_dir=str(config.object_storage.local_base_dir),
                local_tables_dir=str(config.gold_table.local_tables_dir),
                storage_mode=config.object_storage.storage_mode,
            )
        )
        manifest = record_promotion_result(manifest, promotion_summary)
        manifest = finalize_manifest(manifest, "succeeded")
    else:
        manifest = finalize_manifest(manifest, "failed_quality")

    manifest = record_metadata_refs(
        manifest,
        publish_run_metadata(
            manifest,
            manifest_ref=manifest_target.uri,
            local_base_dir=config.object_storage.local_base_dir,
        ),
    )
    write_json_target(manifest_target, manifest)
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError(f"Generated manifest is invalid: {errors}")

    result = dict(manifest)
    result["manifest_uri"] = manifest_target.uri
    result["manifest_path"] = str(manifest_target.local_path) if manifest_target.local_path else None
    return result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = _build_config(args)
    manifest = run_pipeline(config, run_id=args.run_id, contract_path=args.contract_path)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
