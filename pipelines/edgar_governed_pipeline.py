"""Optional-Airflow MWAA DAG definition for the governed EDGAR ETL slice."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.manifests import (
    create_initial_manifest,
    finalize_manifest,
    load_manifest,
    record_ingest_outputs,
    record_promotion_result,
    record_quality_result,
    record_transform_outputs,
    utc_now_iso,
    write_manifest,
)
from thesis_proposed_solution.runtime_config import ObjectStorageConfig
from thesis_proposed_solution.storage import build_manifest_target

PIPELINE_ID = "edgar_governed_pipeline"
DEFAULT_STORAGE_MODE = "s3"
DEFAULT_LOCAL_BASE_DIR = "/tmp/etl-pipeline/object-storage"
DEFAULT_LOCAL_TABLES_DIR = "/tmp/etl-pipeline/s3-tables"

JOB_REFS = {
    "ingest": "jobs/ingest/edgar_ingest.py",
    "transform": "jobs/transform/edgar_transform.py",
    "quality": "jobs/quality/curated_quality_gate.py",
    "promote": "jobs/promote/promote_to_s3_table.py",
}


@dataclass(frozen=True)
class PipelineTaskSpec:
    task_id: str
    task_type: str
    upstream_task_ids: tuple[str, ...]
    command: str | None = None
    branch_targets: tuple[str, ...] = ()


def _object_storage_config_from_conf(conf: Mapping[str, Any]) -> ObjectStorageConfig:
    return ObjectStorageConfig(
        raw_bucket=conf["raw_bucket"],
        raw_prefix=conf["raw_prefix"],
        curated_bucket=conf["curated_bucket"],
        curated_prefix=conf["curated_prefix"],
        manifest_bucket=conf["manifest_bucket"],
        manifest_prefix=conf["manifest_prefix"],
        local_base_dir=Path(conf.get("local_base_dir", DEFAULT_LOCAL_BASE_DIR)),
        storage_mode=conf.get("storage_mode", DEFAULT_STORAGE_MODE),
    )


def _manifest_reference(target) -> str:
    return target.uri if target.storage_mode == "s3" else str(target.local_path)


def _manifest_location_fields(target) -> dict[str, str | None]:
    return {
        "manifest_uri": target.uri,
        "manifest_path": str(target.local_path) if target.local_path else None,
    }


def _build_manifest_target(conf: Mapping[str, Any], run_id: str):
    storage_config = _object_storage_config_from_conf(conf)
    return build_manifest_target(
        storage_config,
        pipeline_id=PIPELINE_ID,
        dataset_date=conf["dataset_date"],
        run_id=run_id,
    )


def _create_base_manifest(conf: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    return create_initial_manifest(
        run_id=run_id,
        pipeline_id=PIPELINE_ID,
        dataset_date=conf["dataset_date"],
        source_ref=conf["source_uri"],
        release_manifest_ref=conf["release_manifest_ref"],
        terraform_state_ref=conf["terraform_state_ref"],
        change_ref=conf["change_ref"],
        gold_table_bucket=conf["gold_table_bucket"],
        gold_namespace=conf["gold_namespace"],
        gold_table=conf["gold_table"],
        job_refs=JOB_REFS,
    )


def _parse_task_summary(payload: Any) -> dict[str, Any] | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    raise TypeError(f"Unsupported task summary payload type: {type(payload)!r}")


def build_run_context(conf: Mapping[str, Any], run_id: str | None = None) -> dict[str, Any]:
    effective_run_id = run_id or conf.get("run_id") or f"airflow-{utc_now_iso().replace(':', '').replace('+00:00', 'z')}"
    manifest_target = _build_manifest_target(conf, effective_run_id)
    manifest = _create_base_manifest(conf, effective_run_id)
    write_manifest(manifest, _manifest_reference(manifest_target))
    return {"run_id": effective_run_id, **_manifest_location_fields(manifest_target)}


def build_final_manifest(
    conf: Mapping[str, Any],
    run_context: Mapping[str, Any],
    *,
    ingest_summary: dict[str, Any] | None,
    transform_summary: dict[str, Any] | None,
    quality_summary: dict[str, Any] | None,
    promotion_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    run_id = str(run_context["run_id"])
    manifest_target = _build_manifest_target(conf, run_id)
    manifest_ref = _manifest_reference(manifest_target)
    try:
        manifest = load_manifest(manifest_ref)
    except Exception:
        manifest = _create_base_manifest(conf, run_id)

    if ingest_summary is not None:
        manifest = record_ingest_outputs(manifest, ingest_summary)
    if transform_summary is not None:
        manifest = record_transform_outputs(manifest, transform_summary)
    if quality_summary is not None:
        manifest = record_quality_result(manifest, quality_summary)
    if promotion_summary is not None:
        manifest = record_promotion_result(manifest, promotion_summary)

    final_status = "failed_quality"
    if quality_summary is not None and quality_summary.get("status") == "passed" and promotion_summary is not None:
        final_status = "succeeded"
    manifest = finalize_manifest(manifest, final_status)
    write_manifest(manifest, manifest_ref)

    result = dict(manifest)
    result.update(_manifest_location_fields(manifest_target))
    return result


def _python_command(script_path: str, arguments: list[str]) -> str:
    return " ".join(["python", script_path, *arguments])


def build_pipeline_spec() -> list[PipelineTaskSpec]:
    shared_storage_args = [
        "--storage-mode {{ dag_run.conf.get('storage_mode', 's3') }}",
        "--local-base-dir {{ dag_run.conf.get('local_base_dir', '/tmp/etl-pipeline/object-storage') }}",
    ]
    shared_governance_args = [
        "--manifest-bucket {{ dag_run.conf['manifest_bucket'] }}",
        "--manifest-prefix {{ dag_run.conf['manifest_prefix'] }}",
        "--release-manifest-ref {{ dag_run.conf['release_manifest_ref'] }}",
        "--terraform-state-ref {{ dag_run.conf['terraform_state_ref'] }}",
        "--change-ref {{ dag_run.conf['change_ref'] }}",
    ]
    run_args = [
        "--run-id {{ ti.xcom_pull(task_ids='initialize_run_context')['run_id'] }}",
        "--dataset-date {{ dag_run.conf['dataset_date'] }}",
    ]

    return [
        PipelineTaskSpec("initialize_run_context", "python", ()),
        PipelineTaskSpec(
            "ingest_edgar_slice",
            "bash",
            ("initialize_run_context",),
            command=_python_command(
                "jobs/ingest/edgar_ingest.py",
                [
                    *run_args,
                    "--source-uri {{ dag_run.conf['source_uri'] }}",
                    "--raw-bucket {{ dag_run.conf['raw_bucket'] }}",
                    "--raw-prefix {{ dag_run.conf['raw_prefix'] }}",
                    *shared_governance_args,
                    *shared_storage_args,
                ],
            ),
        ),
        PipelineTaskSpec(
            "transform_curated_dataset",
            "bash",
            ("ingest_edgar_slice",),
            command=_python_command(
                "jobs/transform/edgar_transform.py",
                [
                    *run_args,
                    "--raw-bucket {{ dag_run.conf['raw_bucket'] }}",
                    "--raw-prefix {{ dag_run.conf['raw_prefix'] }}",
                    "--curated-bucket {{ dag_run.conf['curated_bucket'] }}",
                    "--curated-prefix {{ dag_run.conf['curated_prefix'] }}",
                    *shared_governance_args,
                    *shared_storage_args,
                ],
            ),
        ),
        PipelineTaskSpec(
            "evaluate_curated_quality",
            "bash",
            ("transform_curated_dataset",),
            command=_python_command(
                "jobs/quality/curated_quality_gate.py",
                [
                    *run_args,
                    "--curated-bucket {{ dag_run.conf['curated_bucket'] }}",
                    "--curated-prefix {{ dag_run.conf['curated_prefix'] }}",
                    *shared_governance_args,
                    *shared_storage_args,
                ],
            ),
        ),
        PipelineTaskSpec(
            "branch_on_quality_result",
            "branch",
            ("evaluate_curated_quality",),
            branch_targets=("promote_to_gold_table", "finalize_manifest_status"),
        ),
        PipelineTaskSpec(
            "promote_to_gold_table",
            "bash",
            ("branch_on_quality_result",),
            command=_python_command(
                "jobs/promote/promote_to_s3_table.py",
                [
                    *run_args,
                    "--curated-bucket {{ dag_run.conf['curated_bucket'] }}",
                    "--curated-prefix {{ dag_run.conf['curated_prefix'] }}",
                    "--gold-table-bucket {{ dag_run.conf['gold_table_bucket'] }}",
                    "--gold-namespace {{ dag_run.conf['gold_namespace'] }}",
                    "--gold-table {{ dag_run.conf['gold_table'] }}",
                    "--local-tables-dir {{ dag_run.conf.get('local_tables_dir', '/tmp/etl-pipeline/s3-tables') }}",
                    *shared_governance_args,
                    *shared_storage_args,
                ],
            ),
        ),
        PipelineTaskSpec(
            "finalize_manifest_status",
            "python",
            ("branch_on_quality_result", "promote_to_gold_table"),
        ),
    ]


def dependency_map(spec: list[PipelineTaskSpec] | None = None) -> dict[str, tuple[str, ...]]:
    effective_spec = spec or build_pipeline_spec()
    return {task.task_id: task.upstream_task_ids for task in effective_spec}


def select_quality_branch(quality_result: dict[str, str]) -> str:
    return "promote_to_gold_table" if quality_result.get("status") == "passed" else "finalize_manifest_status"


def initialize_run_context(dag_run=None, **_: object) -> dict[str, Any]:
    conf = dict((dag_run.conf or {}) if dag_run is not None else {})
    return build_run_context(conf)


def finalize_manifest_status(ti=None, dag_run=None, **_: object) -> dict[str, Any]:
    conf = dict((dag_run.conf or {}) if dag_run is not None else {})
    run_context = _parse_task_summary(ti.xcom_pull(task_ids="initialize_run_context")) if ti is not None else None
    if run_context is None:
        raise ValueError("initialize_run_context did not produce run metadata")

    manifest = build_final_manifest(
        conf,
        run_context,
        ingest_summary=_parse_task_summary(ti.xcom_pull(task_ids="ingest_edgar_slice")) if ti is not None else None,
        transform_summary=_parse_task_summary(ti.xcom_pull(task_ids="transform_curated_dataset")) if ti is not None else None,
        quality_summary=_parse_task_summary(ti.xcom_pull(task_ids="evaluate_curated_quality")) if ti is not None else None,
        promotion_summary=_parse_task_summary(ti.xcom_pull(task_ids="promote_to_gold_table")) if ti is not None else None,
    )
    return {
        "status": manifest["status"],
        "manifest_uri": manifest["manifest_uri"],
        "manifest_path": manifest["manifest_path"],
        "dataset_version": manifest["dataset_version"],
    }


try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import BranchPythonOperator, PythonOperator
    from airflow.utils.trigger_rule import TriggerRule
except ImportError:  # pragma: no cover - exercised by import-only tests
    DAG = None
    dag = None
else:
    def _branch_from_airflow_context(ti, **_: object) -> str:
        quality_result = _parse_task_summary(ti.xcom_pull(task_ids="evaluate_curated_quality"))
        if quality_result is None:
            return "finalize_manifest_status"
        return select_quality_branch(quality_result)


    def build_airflow_dag():
        with DAG(
            dag_id=PIPELINE_ID,
            start_date=datetime(2024, 1, 1),
            schedule=None,
            catchup=False,
            render_template_as_native_obj=True,
        ) as airflow_dag:
            tasks = {}
            for spec in build_pipeline_spec():
                if spec.task_type == "python":
                    python_callable = initialize_run_context if spec.task_id == "initialize_run_context" else finalize_manifest_status
                    task = PythonOperator(task_id=spec.task_id, python_callable=python_callable)
                elif spec.task_type == "branch":
                    task = BranchPythonOperator(task_id=spec.task_id, python_callable=_branch_from_airflow_context)
                else:
                    task = BashOperator(task_id=spec.task_id, bash_command=spec.command, do_xcom_push=True)
                tasks[spec.task_id] = task

            tasks["finalize_manifest_status"].trigger_rule = TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS

            for spec in build_pipeline_spec():
                for upstream in spec.upstream_task_ids:
                    tasks[upstream] >> tasks[spec.task_id]
        return airflow_dag


    dag = build_airflow_dag()
