# Implementation Plan

## Objective

Build the thesis prototype in an order that proves the proposed contribution:
an ETL pipeline is not enough on its own; the repository must demonstrate an
end-to-end evidence chain from change request to deployed artifact to runtime
execution to dataset version.

This plan is derived from:

- `../Thesis/chapters/methodology.tex`
- `../Thesis/chapters/baseline_pipeline.tex`
- `../Thesis/chapters/proposed_architecture.tex`
- `../Thesis/diagrams/proposed_pipeline/architecture/hlsa.drawio`
- `../Thesis/diagrams/proposed_pipeline/data_flows/*.drawio`
- `../Thesis/diagrams/proposed_pipeline/process_maps/*.drawio`

## Implementation Scope

This repository is for the proposed architecture shown in the diagrams.

The baseline pipeline is not a parallel build target here. Its role is:

- to act as the control/comparison case in the thesis
- to support evaluation of measurable improvement against R1-R5
- to clarify what governance, lineage, and evidence capabilities were added

The implementation target for this repo is therefore:

- `MWAA + Glue + S3 raw/curated + Amazon S3 Tables gold + Terraform + GitHub
  Actions + OPA + attestation + OpenLineage + OpenMetadata`

That means the build order should optimise for proving the proposed
architecture, not for recreating the baseline first.

## Control Plane Priority

The main focus of the implementation is the control plane, not the ETL runtime
in isolation.

The prototype should therefore prioritise:

- governance of change and release
- policy enforcement before deployment
- attested artifacts and infra references
- correlated runtime evidence
- audit reconstruction from dataset version back to change intent

The runtime ETL path still matters, but it is primarily the substrate on which
the control plane proves auditability and governance.

## Minimum Control Positioning

The controls implemented in this prototype should be treated as representative
minimum controls, not as a claim of production-complete assurance.

In practice this means:

- the checks included in CI/CD and runtime are intentionally sufficient to prove
  the thesis claims
- they are not intended to represent a fully mature enterprise control set
- the thesis text should explicitly state that stronger and broader controls
  would be expected in a production environment

This matters for implementation order: prefer proving the evidence chain end to
end over expanding the number of checks.

## Recommended Build Order

### Phase 0: Freeze the implementation contract

Deliverables:

- one-page implementation contract
- final tool choices for each box in the HLSA
- thesis-to-implementation mapping for R1-R5
- explicit statement that the prototype implements minimum illustrative
  controls focused on the control plane

Status:

- Completed by [implementation-contract.md](./implementation-contract.md) and
  [control-matrix.md](./control-matrix.md)

Why first:

- Otherwise the repo can drift away from the proposed architecture that the
  thesis is evaluating.

Exit criteria:

- every major diagram box maps to a real service, repo folder, or workflow
- every requirement R1-R5 has at least one planned technical control

### Phase 1: Create the repository skeleton

Build:

- `infra/` for Terraform
- `pipelines/` for DAG/workflow definitions
- `jobs/ingest/` and `jobs/transform/`
- `policies/` for OPA/Rego
- `schemas/` or `contracts/` for data contracts
- `scripts/` for local/dev automation
- `docs/` for evidence model, runbook, and demo steps
- `.github/workflows/` for CI/CD

Also define:

- branch naming tied to issue IDs
- PR template
- issue template for change requests
- CODEOWNERS

Status:

- Completed by the Stage 1 repository scaffold, governance templates, workflow
  placeholders, and shared Python package layout

Why here:

- R1 starts at change management, not at runtime.

Exit criteria:

- a change can be opened as an issue, implemented on a linked branch, and
  reviewed through a PR with the right owners

### Phase 2: Stand up the minimum data platform

Build only the runtime foundation first:

- S3 buckets or prefixes for raw, curated, manifests, and MWAA artifacts
- Amazon S3 Tables bucket and namespace for the managed Iceberg gold layer
- catalog foundation
- IAM roles
- secrets management
- logging/monitoring plumbing

Keep this phase intentionally thin:

- no advanced lineage yet
- no full audit UI yet
- only enough infra to execute one governed pipeline

Why before CI hardening:

- you need a stable target for deployment and runtime evidence capture

Exit criteria:

- Terraform can provision the platform repeatedly
- a test workload can read source data and write a controlled object to S3

### Phase 3: Implement the simplest end-to-end ETL slice

Pick one narrow pipeline:

- ingest a small EDGAR subset
- validate schema
- write raw data
- transform to curated
- promote one gold dataset/table

Do not build breadth yet.

Design rules:

- every run must emit a run ID
- every output path/table version must be attributable to that run ID
- every stage must be deterministic enough to replay during evaluation
- MWAA acts as orchestrator only; Glue Python jobs perform ingestion,
  transformation, and quality validation
- raw and curated remain simple S3 zones; gold is the governed Amazon S3
  Tables layer

Exit criteria:

- one manual or scheduled run produces a gold dataset from source to finish
- the run can be repeated with explainable output

### Phase 4: Add CI/CD controls before adding complexity

Implement the minimum blocking controls needed to make the control plane
credible:

- linting and unit tests
- integration tests for the pipeline
- IaC validation
- SAST/SCA/secrets scanning
- OPA policy checks
- ticket/branch/PR enforcement
- required approvals from code owner and data owner

This phase is what converts a working repo into a governed repo.

These controls should be treated as the minimum representative set for the
prototype. Do not expand them prematurely at the cost of delaying evidence
capture and audit-chain reconstruction.

Exit criteria:

- an unapproved or policy-violating change cannot be merged or deployed
- CI generates machine-readable evidence of the checks performed

### Phase 5: Build artifact packaging, release, and attestation

Implement:

- versioned workflow artifact packaging
- release creation from approved builds
- provenance/attestation generation
- deployment only from approved artifacts

Minimum proof required:

- runtime execution consumes a specific approved artifact version
- you can show `commit -> CI run -> artifact -> attestation -> deployment`
- deployment updates the MWAA workflow bundle and the referenced Glue job
  package/version

Exit criteria:

- a deployed workflow/job version is cryptographically or at least
  platform-attested and referenceable from runtime metadata

### Phase 6: Capture runtime metadata and evidence

Now add the evidence chain around the ETL run:

- run metadata store or structured run records
- execution logs with retained run correlation IDs
- infra state/version reference
- artifact version reference
- issue/change reference

For each run, record at minimum:

- run ID
- source input version or extraction timestamp
- deployed artifact version
- infra version/state reference
- output dataset/table version
- status, timestamps, and row counts
- approval and policy evaluation references where relevant

Exit criteria:

- you can answer "which run produced this dataset version?" without manual log
  archaeology
- the evidence chain can continue from `dataset -> run -> artifact -> infra ->
  change`

### Phase 7: Add lineage and metadata governance

Implement the evidence spine from the diagrams:

- OpenLineage event emission
- catalog metadata updates
- OpenMetadata integration
- dataset/version references for Iceberg or equivalent table layer
- change, artifact, and infra references surfaced into the metadata layer

This is where R5 becomes defensible.

Exit criteria:

- a gold dataset version can be traced to upstream datasets, run metadata,
  artifact version, infra reference, and originating change

### Phase 8: Implement audit reconstruction queries

Build the smallest useful audit surface:

- script, notebook, API endpoint, or dashboard query
- primary lookup by dataset version
- secondary lookup by run ID, release, or issue ID if useful
- reconstructed chain:
  `dataset -> run -> artifact -> infra -> change`

Do not overbuild a UI. For the thesis, a reproducible query/report is enough.

Exit criteria:

- you can run a repeatable demo that answers:
  - why did this dataset change?
  - which run produced it?
  - which code revision/artifact was responsible?
  - which approved change triggered that revision?

### Phase 9: Add resilience and replay scenarios

Implement only the controls needed for R3 evaluation:

- replay a prior run against preserved inputs/config
- compare outputs
- show explainable consistency or controlled divergence
- capture failed-run evidence and recovery steps

Exit criteria:

- at least one historical state can be replayed for thesis evaluation

### Phase 10: Prepare the thesis demonstration pack

Create:

- seeded demo dataset/sample run inputs
- reproducible demo script
- screenshots/evidence exports
- mapping from demo evidence to R1-R5
- explicit comparison points against the baseline pipeline

For each requirement, prepare a short baseline-vs-proposed comparison:

- what the baseline could not prove
- what the proposed architecture records or enforces
- what measurable evidence demonstrates the improvement

Also prepare a short statement for the thesis text explaining that:

- the control plane is the primary contribution
- the checks implemented are minimum illustrative controls
- the prototype demonstrates governance improvement rather than exhaustive
  operational hardening

This should be treated as a product deliverable, not an afterthought.

Exit criteria:

- you can execute the demo in a fixed order without improvisation

## Practical Sequence For The First Few Weeks

If you want the shortest path to visible progress, do the work in this order:

1. Freeze implementation choices and repository structure.
2. Provision base AWS resources with Terraform.
3. Get one ingestion job and one transform job running end to end.
4. Add GitHub issue/PR discipline, CODEOWNERS, and branch rules.
5. Add CI checks, security scans, and OPA policy gates.
6. Package and attest deployment artifacts.
7. Record runtime metadata with stable IDs.
8. Integrate OpenLineage and OpenMetadata.
9. Build audit reconstruction queries and replay tests.
10. Write the thesis implementation and evaluation chapters from the evidence
    you generated.

## What Not To Do Early

- Do not start with a polished audit dashboard.
- Do not model every possible dataset or business rule.
- Do not add multiple pipelines before one pipeline has a complete evidence
  chain.
- Do not chase performance tuning before lineage, attestation, and replay work.
- Do not implement policy-as-code after deployment; it must block changes early.

## Suggested Definition Of Done

The prototype is "done enough" for the thesis when all of the following are
true:

- A change begins as a GitHub issue and passes through PR approval.
- CI enforces tests, security checks, and policy checks before release.
- Deployment uses an approved artifact with provenance/attestation.
- A runtime execution produces a versioned dataset/table.
- Metadata links that dataset version back to run, artifact, infra, and change.
- An audit query reconstructs the chain without manual correlation.
- A historical run can be replayed for evaluation.

## Recommended Milestone Structure

### Milestone 1: Running Baseline In The New Repo

- repo skeleton
- Terraform foundation
- one ETL path working

### Milestone 2: Governed Delivery

- issue/PR workflow
- CI/CD controls
- policy gates
- approvals
- artifact versioning/attestation

### Milestone 3: Evidence Chain

- runtime metadata
- lineage emission
- catalog metadata
- audit reconstruction query

### Milestone 4: Evaluation Ready

- replay test
- failure/recovery scenario
- thesis screenshots, tables, and demo script

## Evaluation Framing

The implementation should be designed so each major control has a clear
baseline comparison. Useful comparison axes are:

- change traceability: baseline implicit vs proposed issue-to-PR-to-release
- deployment integrity: baseline mutable/unsigned vs proposed attested artifact
- runtime evidence: baseline scattered logs vs proposed correlated run metadata
- lineage reconstruction: baseline manual collation vs proposed queryable chain
- replay/recovery: baseline weak reproducibility vs proposed version-linked
  replay

## Recommended Next Action

Start by writing an implementation contract that answers these four questions:

1. Which exact AWS services and open-source tools map to each diagram box?
2. Where will run metadata live before or alongside OpenMetadata?
3. What exact artifact will be attested and deployed into MWAA/Glue?
4. What measurable baseline-vs-proposed indicators will you capture for R1-R5?

Once those are fixed, build the repo skeleton and the Terraform foundation
immediately.
