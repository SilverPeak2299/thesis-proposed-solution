# Implementation Contract

## Purpose

This document closes Phase 0 of the implementation plan by fixing the
implementation target for the proposed architecture. It is the build contract
for this repository.

The baseline pipeline is not implemented in this repository. It exists only as
the comparator used in thesis evaluation.

## Primary Thesis Position

The primary contribution of this prototype is the control plane:

- change governance
- policy enforcement
- artifact provenance
- infrastructure traceability
- runtime evidence capture
- audit reconstruction

The ETL runtime exists to provide a realistic execution substrate for those
controls. The controls implemented here are representative minimum controls for
the thesis prototype, not a claim of production-complete hardening.

## Fixed Architecture Decisions

- Cloud target: AWS-first
- Orchestration: Amazon MWAA
- Compute: AWS Glue Python jobs
- Data zones: S3 raw, S3 curated, Amazon S3 Tables gold
- Governed analytical layer: managed Iceberg via Amazon S3 Tables at gold only
- Infrastructure as code: Terraform
- CI/CD: GitHub Actions
- Change management: GitHub Issues + Pull Requests
- Human approvals: Code Owner + Data Owner
- Policy engine: OPA executed in PR/CI gates
- Artifact provenance: GitHub native attestation
- Infra reference: Terraform state version
- Authoritative run metadata: versioned S3 JSON manifests
- Lineage event model: OpenLineage emitted by orchestrated jobs
- Metadata and audit hub: OpenMetadata
- OpenMetadata hosting: containerised deployment on EC2
- Data quality component name: `Data Quality Framework`

## Major Component Mapping

| Architecture box | Implementation |
| --- | --- |
| GitHub Issue / change request | GitHub Issues with issue templates and required issue linkage |
| Pull Request + approval gate | GitHub Pull Requests with branch protections, CODEOWNERS, and required reviewers |
| GitHub Actions | CI/CD runner for tests, policy evaluation, packaging, attestation, and deployment |
| OPA policy engine | OPA policy evaluation in PR and CI workflows |
| Approved artifact / release | Logical release manifest referencing immutable deployable assets |
| GitHub native attestation | Provenance attached to the approved release manifest and artifact set |
| Terraform | IaC for AWS resources, with the applied Terraform state version captured as evidence |
| MWAA | Orchestrator only; schedules and triggers Glue jobs and control steps |
| Glue Python jobs | Ingestion, transformation, and data quality execution |
| S3 raw zone | Landing zone for extracted source data |
| S3 curated zone | Intermediate transformed zone before governed promotion |
| Amazon S3 Tables gold / managed Iceberg | Final governed analytical dataset layer with versionable table state |
| Glue Crawler | Metadata scan of governed outputs where needed |
| Glue Data Catalog | AWS catalog context for tables and schema metadata |
| OpenLineage | Lineage events emitted from orchestrated runtime jobs |
| OpenMetadata | Central metadata, evidence, and audit query hub |
| CloudWatch | Execution logs and operational telemetry |
| IAM Roles | Execution and service identity boundaries |
| Secrets Manager | Secret storage for runtime and service credentials |
| S3 JSON manifests | Authoritative run records and evidence manifests linked to outputs |

## Release And Deployment Model

The deployable unit is a single logical release manifest.

Each approved release manifest must reference:

- an immutable MWAA DAG bundle
- an immutable Glue job script or package version
- the Terraform state version for the target environment
- the GitHub CI run that produced the release
- the GitHub native attestation/provenance record

This is a logical release unit rather than a single physical file. The reason
is that MWAA and Glue are deployed as separate runtime assets, but the thesis
needs one auditable control-plane object that links them together.

Deployment path:

1. GitHub Actions runs tests, policy checks, and packaging.
2. GitHub Actions creates the logical release manifest.
3. GitHub Actions records or links the GitHub native attestation.
4. GitHub Actions deploys the MWAA DAG bundle and the referenced Glue job
   package/version.
5. Runtime executions record the release manifest reference in run evidence.

## Runtime And Evidence Model

The runtime path is:

1. MWAA triggers a Glue ingestion job.
2. The ingestion job writes source data to S3 raw.
3. MWAA triggers a Glue transformation job.
4. The transformation job writes outputs to S3 curated.
5. MWAA triggers the `Data Quality Framework` as a Glue-executed control step.
6. Promotion to gold is allowed only if:
   - the quality/contract checks pass
   - the runtime is using an approved attested release
7. The promoted output is written to the Amazon S3 Tables gold layer.

For every governed run, the system must capture at minimum:

- run ID
- source extraction timestamp or source version
- release manifest reference
- MWAA bundle reference
- Glue job package/version reference
- Terraform state version
- issue/change reference
- approval reference
- policy evaluation reference
- output dataset version
- status, timestamps, and row counts

The authoritative run record is stored as a versioned S3 JSON manifest.
OpenMetadata is the query hub, but S3 manifests are the authoritative stored run
evidence.

Primary audit chain:

`dataset version -> run manifest -> release manifest -> Terraform state version -> change request`

Primary audit lookup key:

`dataset version`

## Quantitative Evaluation Position

Phase 0 fixes the prototype to use metrics, not thresholds.

The thesis should quantify measurable improvement where possible, but should
not commit this early to hard thresholds that may later prove unrealistic for
the prototype.

The required metric set is defined in
[control-matrix.md](./control-matrix.md).

## Assumptions And Defaults

- OPA is the minimum policy mechanism; this contract does not require a broader
  enterprise policy stack.
- OpenLineage events feed OpenMetadata directly; a separate lineage backend is
  not required for the prototype.
- OpenMetadata is a real deployed service in the target architecture, not a
  conceptual placeholder.
- Gold is the only Iceberg-managed layer and is implemented with Amazon S3
  Tables. Raw and curated remain simpler S3 zones to reduce platform
  complexity.
- Glue uses Python jobs in the prototype for cost reasons. This is a runtime
  implementation choice, not a thesis claim that Python jobs are the only valid
  production design.
