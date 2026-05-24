# Local Airflow development

## Purpose

Use Docker-based Apache Airflow for day-to-day DAG development and dry runs
while the AWS target remains dormant. This keeps the orchestration code
exerciseable without paying for a continuously running MWAA environment.

Local Airflow is a development surface, not the governed production-equivalent
runtime used for thesis evaluation. Governed runs and release evidence still
target the AWS deployment path when MWAA is re-enabled.

## Start local Airflow

From the repository root:

```bash
docker compose -f docker-compose.airflow.yml up
```

This starts:

- a local Airflow `standalone` container at `http://localhost:8080`
- a local OpenMetadata server at `http://localhost:8585`
- local MySQL and Elasticsearch dependencies for OpenMetadata

The default OpenMetadata UI login is `admin@open-metadata.org` / `admin`.

The repository is mounted into the Airflow container so the existing DAG and
job entrypoints can run unchanged.

The web UI is exposed on `http://localhost:8080`.

The container uses:

- `pipelines/` as the Airflow DAG folder
- `jobs/` for the ETL job entrypoints
- `src/` on `PYTHONPATH` for shared code
- the repo working tree as `AIRFLOW_HOME`

## Trigger the governed DAG locally

The DAG id is `edgar_governed_pipeline`.

Example local run configuration:

```json
{
  "dataset_date": "2024-01-31",
  "source_uri": "/opt/airflow/tests/fixtures/edgar_sample/submissions.json",
  "raw_bucket": "local-raw",
  "raw_prefix": "edgar/raw",
  "curated_bucket": "local-curated",
  "curated_prefix": "edgar/curated",
  "manifest_bucket": "local-manifests",
  "manifest_prefix": "governed-runs",
  "release_manifest_ref": "release-manifests/local-dev.json",
  "terraform_state_ref": "terraform-state/local-docker-airflow.json",
  "change_ref": "changes/local-dev.json",
  "gold_table_bucket": "local-gold-bucket",
  "gold_namespace": "edgar",
  "gold_table": "filings",
  "storage_mode": "local",
  "local_base_dir": "/opt/airflow/.local-data/object-storage",
  "local_tables_dir": "/opt/airflow/.local-data/s3-tables"
}
```

This uses the same pipeline code as `scripts/run_local_etl.py`, but through the
Airflow DAG path instead of the direct local runner.

The local run now validates that the referenced release manifest, Terraform
state record, and change record exist before the DAG starts.

Successful runs also emit local metadata artifacts under `.local-data/metadata/`
including:

- an OpenLineage-style completion event
- an OpenMetadata-style run record
- an OpenMetadata-style gold dataset record
- an audit-chain record keyed by `dataset_version`

When the local OpenMetadata service is running, the DAG finalization step also
logs into OpenMetadata and submits the same completion event to the live
OpenLineage ingestion endpoint at `/api/v1/openlineage/lineage`.

If you want to check the service before triggering the DAG:

```bash
curl http://localhost:8585/api/v1/system/version
```

## Tear down and later redeploy MWAA

The dev Terraform environment now exposes `enable_mwaa`.

- Keep `enable_mwaa = false` to develop locally in Docker only.
- Set `enable_mwaa = true` when you want Terraform to provision MWAA again.

If MWAA already exists in the dev environment, applying Terraform with
`enable_mwaa = false` will plan its removal while keeping the remaining dev
platform foundation intact.
