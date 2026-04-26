# thesis-proposed-solution

This repository contains the proposed architecture implementation for the
thesis. The baseline pipeline is not built here; it remains the comparison
case used in evaluation.

Current key docs:

- [Implementation plan](./docs/implementation-plan.md)
- [Implementation contract](./docs/implementation-contract.md)
- [R1-R5 control matrix](./docs/control-matrix.md)
- [Repository conventions](./docs/repository-conventions.md)
- [Contributor runbook](./docs/contributor-runbook.md)

Stage 1 scaffolding now reserves the main implementation areas:

- `infra/` for Terraform
- `pipelines/` for MWAA assets
- `jobs/` for Glue Python jobs
- `policies/` for OPA/Rego
- `contracts/` for data contracts
- `src/` for shared Python code
- `tests/` for future test coverage
