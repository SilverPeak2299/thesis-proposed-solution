# R1-R5 Control Matrix

## Purpose

This matrix fixes the minimum controls, evidence outputs, and quantitative
metrics for the proposed architecture. It is the reference used to evaluate the
proposed implementation against the baseline.

The controls listed here are representative minimum controls for the thesis
prototype.

## Control Matrix

| Requirement | Minimum control | Evidence emitted | Quantitative metrics |
| --- | --- | --- | --- |
| R1 Governance Accountability | Every production-relevant change must link to a GitHub Issue, pass PR review, and receive Code Owner + Data Owner approval before release | Issue reference, PR reference, reviewer approvals, release manifest change reference | `Change traceability coverage = traced changes / total governed changes`; `Dual approval coverage = changes with both approvals / total governed changes`; `Release linkage coverage = releases linked to change IDs / total releases` |
| R2 Information Security Assurance | Every deployable release must pass minimum CI security checks and carry GitHub native attestation before deployment | CI check results, policy pass/fail record, attestation reference, release manifest artifact references | `Artifact attestation coverage = attested releases / total releases`; `Security gate pass rate = releases passing minimum security gates / total release attempts`; `Undeployed failed-release count = failed-gate releases not deployed` |
| R3 Operational Risk Control | Every governed run must emit a reproducible run manifest linked to code, infra, and output version, with replay supported for selected historical states | Versioned S3 JSON run manifest, release manifest reference, Terraform state version, dataset version, replay result record | `Run manifest coverage = runs with valid manifests / total governed runs`; `Replay success rate = successful replayed runs / replay attempts`; `Output reconstruction coverage = dataset versions linked to run manifests / total gold dataset versions` |
| R4 Continuous Control Monitoring | PR and CI workflows must enforce OPA policy, validation checks, and approval conditions before deployment | Policy evaluation results, CI run records, blocked deployment evidence, merged change evidence | `Policy enforcement coverage = changes evaluated by policy / total governed changes`; `Blocked violation count = release attempts blocked by policy`; `Unchecked deployment rate = deployments without completed control evaluation / total deployments` |
| R5 End-to-End Evidence Chain | Each promoted gold dataset version must be reconstructable to run, artifact, infra, and change without manual log collation | Dataset version reference, run manifest, release manifest, Terraform state version, change reference, metadata references in OpenMetadata | `Audit reconstruction success rate = successful end-to-end reconstructions / audit attempts`; `Dataset traceability coverage = gold dataset versions linked to full chain / total gold dataset versions`; `Manual-correlation exceptions = audit cases requiring manual log collation` |

## Metric Definitions

### Governed changes

Changes that are intended to reach deployable runtime or infrastructure state.
This excludes purely local experiments and discarded work.

### Governed runs

Runs executed from approved runtime assets and intended to produce traceable
pipeline outputs.

### Gold dataset version

A promoted governed output version in the Iceberg-backed gold layer.

### Successful audit reconstruction

An audit lookup starting from a dataset version can identify all of the
following without manual log collation:

- run manifest
- release manifest
- Terraform state version
- originating change reference

### Manual log collation

Any audit case where the operator must inspect unrelated raw logs across
multiple systems because the required references are not already linked through
the evidence chain.

## Baseline Comparison Position

The baseline is expected to underperform the proposed architecture on the
metrics above because it lacks:

- enforced dual approvals
- policy-as-code gate evidence
- attested release artifacts
- authoritative run manifests
- unified metadata/evidence linkage

The thesis should compare baseline and proposed results using the same metric
definitions wherever possible.

## Phase 0 Completion Note

Phase 0 is complete when this matrix is used together with
[implementation-contract.md](./implementation-contract.md) as the fixed
specification for the rest of the build.
