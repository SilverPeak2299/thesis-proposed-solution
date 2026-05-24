# thesis-proposed-solution

This repository contains the proposed architecture implementation for the
thesis. The baseline pipeline is not built here; it remains the comparison
case used in evaluation.

Current key docs:

- [Implementation plan](./docs/implementation-plan.md)
- [Implementation contract](./docs/implementation-contract.md)
- [R1-R5 control matrix](./docs/control-matrix.md)
- [Local Airflow development](./docs/local-airflow-development.md)
- [Repository conventions](./docs/repository-conventions.md)
- [Contributor runbook](./docs/contributor-runbook.md)

Stage 1 scaffolding now reserves the main implementation areas:

- `infra/` for Terraform
- `pipelines/` for Airflow assets that can run locally in Docker and later on MWAA
- `docker-compose.airflow.yml` for the local Airflow plus OpenMetadata development stack
- `jobs/` for Glue Python jobs
- `policies/` for OPA/Rego
- `contracts/` for data contracts
- `release-manifests/` for sample logical release manifests used by local validation
- `terraform-state/` for sample Terraform state reference records used by local validation
- `changes/` for sample change records used by local validation
- `runtime-configs/` for generated runtime inputs tied to governed release evidence
- `src/` for shared Python code
- `tests/` for future test coverage

The `Release Controls` GitHub Actions workflow now packages an attested release
bundle and emits:

- a generated release manifest under `release-manifests/`
- a generated change record under `changes/`
- a generated runtime config under `runtime-configs/`
- release evidence and the Sigstore attestation bundle under `build/release-controls/`
