# Pipelines

This directory contains Airflow orchestration assets.

The intended workflow is:

- develop and dry run DAGs locally in Docker-based Airflow
- keep DAG code compatible with later deployment to MWAA
- treat MWAA as the AWS runtime target, not the always-on development surface

Planned contents:

- DAG definitions
- DAG packaging assets for release manifests and later MWAA deployment
- orchestration code that triggers Glue ingestion, transform, and quality steps
