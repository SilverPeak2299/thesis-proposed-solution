from __future__ import annotations

import json
from pathlib import Path

from thesis_proposed_solution.runtime_config import (
    apply_runtime_overrides,
    load_runtime_config,
)


def test_load_runtime_config_and_apply_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime-config.json"
    config_path.write_text(
        json.dumps(
            {
                "pipeline_id": "edgar_governed_pipeline",
                "dataset_date": "2024-01-31",
                "source_uri": "/tmp/source.json",
                "object_storage": {
                    "raw_bucket": "raw-bucket",
                    "raw_prefix": "raw/prefix",
                    "curated_bucket": "curated-bucket",
                    "curated_prefix": "curated/prefix",
                    "manifest_bucket": "manifest-bucket",
                    "manifest_prefix": "manifest/prefix",
                    "local_base_dir": str(tmp_path / "object-storage"),
                },
                "gold_table": {
                    "gold_table_bucket": "gold-bucket",
                    "gold_namespace": "edgar",
                    "gold_table": "filings",
                    "local_tables_dir": str(tmp_path / "tables"),
                },
                "governance": {
                    "release_manifest_ref": "release.json",
                    "terraform_state_ref": "tfstate/1",
                    "change_ref": "issue/1",
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)
    overridden = apply_runtime_overrides(
        config,
        dataset_date="2024-02-01",
        gold_table="daily_filings",
        local_tables_dir=tmp_path / "replay-tables",
    )

    assert config.dataset_date == "2024-01-31"
    assert overridden.dataset_date == "2024-02-01"
    assert overridden.gold_table.gold_table == "daily_filings"
    assert overridden.gold_table.local_tables_dir == tmp_path / "replay-tables"
