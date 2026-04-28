"""Optional-Airflow MWAA DAG definition for the governed EDGAR ETL slice."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thesis_proposed_solution.manifests import utc_now_iso

PIPELINE_ID = "edgar_governed_pipeline"


@dataclass(frozen=True)
class PipelineTaskSpec:
    task_id: str
    task_type: str
    upstream_task_ids: tuple[str, ...]
    command: str | None = None
    branch_targets: tuple[str, ...] = ()


def build_pipeline_spec() -> list[PipelineTaskSpec]:
    return [
        PipelineTaskSpec("initialize_run_context", "python", ()),
        PipelineTaskSpec(
            "ingest_edgar_slice",
            "bash",
            ("initialize_run_context",),
            command="python jobs/ingest/edgar_ingest.py --run-id {{ ti.xcom_pull(task_ids='initialize_run_context')['run_id'] }} --dataset-date {{ dag_run.conf['dataset_date'] }} --source-uri {{ dag_run.conf['source_uri'] }} --raw-bucket {{ dag_run.conf['raw_bucket'] }} --raw-prefix {{ dag_run.conf['raw_prefix'] }} --manifest-bucket {{ dag_run.conf['manifest_bucket'] }} --manifest-prefix {{ dag_run.conf['manifest_prefix'] }} --release-manifest-ref {{ dag_run.conf['release_manifest_ref'] }} --terraform-state-ref {{ dag_run.conf['terraform_state_ref'] }} --change-ref {{ dag_run.conf['change_ref'] }}",
        ),
        PipelineTaskSpec(
            "transform_curated_dataset",
            "bash",
            ("ingest_edgar_slice",),
            command="python jobs/transform/edgar_transform.py --run-id {{ ti.xcom_pull(task_ids='initialize_run_context')['run_id'] }} --dataset-date {{ dag_run.conf['dataset_date'] }} --raw-bucket {{ dag_run.conf['raw_bucket'] }} --raw-prefix {{ dag_run.conf['raw_prefix'] }} --curated-bucket {{ dag_run.conf['curated_bucket'] }} --curated-prefix {{ dag_run.conf['curated_prefix'] }} --manifest-bucket {{ dag_run.conf['manifest_bucket'] }} --manifest-prefix {{ dag_run.conf['manifest_prefix'] }} --release-manifest-ref {{ dag_run.conf['release_manifest_ref'] }} --terraform-state-ref {{ dag_run.conf['terraform_state_ref'] }} --change-ref {{ dag_run.conf['change_ref'] }}",
        ),
        PipelineTaskSpec(
            "evaluate_curated_quality",
            "bash",
            ("transform_curated_dataset",),
            command="python jobs/quality/curated_quality_gate.py --run-id {{ ti.xcom_pull(task_ids='initialize_run_context')['run_id'] }} --dataset-date {{ dag_run.conf['dataset_date'] }} --curated-bucket {{ dag_run.conf['curated_bucket'] }} --curated-prefix {{ dag_run.conf['curated_prefix'] }} --manifest-bucket {{ dag_run.conf['manifest_bucket'] }} --manifest-prefix {{ dag_run.conf['manifest_prefix'] }} --release-manifest-ref {{ dag_run.conf['release_manifest_ref'] }} --terraform-state-ref {{ dag_run.conf['terraform_state_ref'] }} --change-ref {{ dag_run.conf['change_ref'] }}",
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
            command="python jobs/promote/promote_to_s3_table.py --run-id {{ ti.xcom_pull(task_ids='initialize_run_context')['run_id'] }} --dataset-date {{ dag_run.conf['dataset_date'] }} --curated-bucket {{ dag_run.conf['curated_bucket'] }} --curated-prefix {{ dag_run.conf['curated_prefix'] }} --manifest-bucket {{ dag_run.conf['manifest_bucket'] }} --manifest-prefix {{ dag_run.conf['manifest_prefix'] }} --gold-table-bucket {{ dag_run.conf['gold_table_bucket'] }} --gold-namespace {{ dag_run.conf['gold_namespace'] }} --gold-table {{ dag_run.conf['gold_table'] }} --release-manifest-ref {{ dag_run.conf['release_manifest_ref'] }} --terraform-state-ref {{ dag_run.conf['terraform_state_ref'] }} --change-ref {{ dag_run.conf['change_ref'] }}",
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


def initialize_run_context() -> dict[str, str]:
    return {"run_id": f"airflow-{utc_now_iso().replace(':', '').replace('+00:00', 'z')}"}


def finalize_manifest_status(**_: object) -> dict[str, str]:
    return {"status": "finalized"}


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
        quality_result = ti.xcom_pull(task_ids="evaluate_curated_quality")
        if isinstance(quality_result, str):
            import json

            quality_result = json.loads(quality_result)
        return select_quality_branch(quality_result)


    def build_airflow_dag():
        with DAG(
            dag_id=PIPELINE_ID,
            start_date=None,
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
                    task = BashOperator(task_id=spec.task_id, bash_command=spec.command)
                tasks[spec.task_id] = task

            tasks["finalize_manifest_status"].trigger_rule = TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS

            for spec in build_pipeline_spec():
                for upstream in spec.upstream_task_ids:
                    tasks[upstream] >> tasks[spec.task_id]
        return airflow_dag


    dag = build_airflow_dag()
