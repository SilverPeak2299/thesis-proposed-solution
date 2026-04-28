from __future__ import annotations

from thesis_proposed_solution.manifests import compute_dataset_version


def test_dataset_version_is_stable_for_same_table_identity_and_write_result() -> None:
    write_result = {
        "dataset_date": "2024-01-31",
        "row_count": 2,
        "content_digest": "abc123",
        "source_curated_uri": "s3://curated/records.jsonl",
        "write_mode": "append",
    }

    first = compute_dataset_version(
        gold_table_bucket="gold-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        write_result=write_result,
    )
    second = compute_dataset_version(
        gold_table_bucket="gold-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        write_result=write_result,
    )

    assert first == second


def test_dataset_version_changes_with_table_identity() -> None:
    write_result = {
        "dataset_date": "2024-01-31",
        "row_count": 2,
        "content_digest": "abc123",
        "source_curated_uri": "s3://curated/records.jsonl",
        "write_mode": "append",
    }

    first = compute_dataset_version(
        gold_table_bucket="gold-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        write_result=write_result,
    )
    second = compute_dataset_version(
        gold_table_bucket="other-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        write_result=write_result,
    )

    assert first != second


def test_dataset_version_does_not_need_run_specific_uris_for_replay() -> None:
    replay_stable = {
        "dataset_date": "2024-01-31",
        "row_count": 2,
        "content_digest": "abc123",
        "write_mode": "append",
    }

    first = compute_dataset_version(
        gold_table_bucket="gold-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        write_result=replay_stable,
    )
    second = compute_dataset_version(
        gold_table_bucket="gold-bucket",
        gold_namespace="edgar",
        gold_table="filings",
        write_result={**replay_stable},
    )

    assert first == second
