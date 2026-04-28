from __future__ import annotations

from pipelines.edgar_governed_pipeline import (
    build_pipeline_spec,
    dependency_map,
    select_quality_branch,
)


def test_pipeline_spec_has_expected_task_order_and_dependencies() -> None:
    spec = build_pipeline_spec()
    dependencies = dependency_map(spec)

    assert [task.task_id for task in spec] == [
        "initialize_run_context",
        "ingest_edgar_slice",
        "transform_curated_dataset",
        "evaluate_curated_quality",
        "branch_on_quality_result",
        "promote_to_gold_table",
        "finalize_manifest_status",
    ]
    assert dependencies["ingest_edgar_slice"] == ("initialize_run_context",)
    assert dependencies["transform_curated_dataset"] == ("ingest_edgar_slice",)
    assert dependencies["evaluate_curated_quality"] == ("transform_curated_dataset",)
    assert dependencies["branch_on_quality_result"] == ("evaluate_curated_quality",)
    assert dependencies["promote_to_gold_table"] == ("branch_on_quality_result",)
    assert dependencies["finalize_manifest_status"] == (
        "branch_on_quality_result",
        "promote_to_gold_table",
    )


def test_quality_branch_blocks_promotion_when_quality_fails() -> None:
    assert select_quality_branch({"status": "passed"}) == "promote_to_gold_table"
    assert select_quality_branch({"status": "failed"}) == "finalize_manifest_status"
