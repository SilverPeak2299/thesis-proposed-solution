# Contributor Runbook

## Starting Work

1. Open or identify the governing GitHub Issue.
2. Create a branch using `<issue-id>/<short-name>`.
3. Confirm which phase and which of R1-R5 the change affects.

## Making Changes

When working in this repository, prefer changes that improve:

- traceability
- policy enforcement
- provenance
- runtime evidence capture
- audit reconstruction

Runtime complexity should not be added unless it supports those goals.

## Opening A Pull Request

Before opening a PR, capture:

- the linked issue
- the affected stage or requirements
- the evidence, control, and runtime impact
- any follow-up work that later stages must complete

## Updating Docs

If a change affects the meaning of the architecture, release model, or evidence
chain, update:

- `docs/implementation-contract.md`
- `docs/control-matrix.md`
- `docs/implementation-plan.md`

as needed so Phase 0 and Stage 1 remain aligned.
