# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains Phase 0 architecture and planning documents:

- `README.md`: entry point for the repo
- `docs/implementation-plan.md`: staged build order
- `docs/implementation-contract.md`: fixed architecture decisions
- `docs/control-matrix.md`: R1-R5 controls, evidence, and metrics

As implementation begins, keep the planned structure from the implementation plan:

- `infra/`: Terraform and AWS infrastructure definitions
- `pipelines/`: MWAA DAGs and orchestration assets
- `jobs/`: Glue Python jobs for ingest, transform, and quality checks
- `policies/`: OPA/Rego policies
- `schemas/` or `contracts/`: data contracts and validation inputs
- `scripts/`: local automation and audit/replay helpers

## Build, Test, and Development Commands

There is no application build system yet. For now, contributors should use:

- `git status`: review local changes before and after edits
- `rg --files .`: inspect the repo quickly
- `sed -n '1,160p' docs/implementation-contract.md`: review key architecture decisions

When code is added, document the canonical test and build commands here rather than inventing per-branch workflows.

## Coding Style & Naming Conventions

Use ASCII by default. Prefer short, readable files and explicit names.

- Markdown: sentence case headings, short sections, direct language
- Python: 4-space indentation, `snake_case` for files and functions
- Terraform: one resource concern per file where practical
- Policies: name files by control purpose, for example `release_approval.rego`

Keep naming aligned to the architecture vocabulary: `mwaa`, `glue`, `gold`, `iceberg`, `openmetadata`, `run_manifest`.

## Testing Guidelines

This repo is currently document-first, so testing is review-based:

- verify changes against `docs/implementation-contract.md`
- keep `docs/control-matrix.md` and `docs/implementation-plan.md` consistent
- prefer quantitative evaluation definitions where possible

When tests are introduced, place them near the relevant subsystem and use names like `test_run_manifest.py` or `release_policy_test.rego`.

## Commit & Pull Request Guidelines

The current history uses short imperative commits, for example `Initial commit`. Continue that style:

- `Add implementation contract`
- `Define R1-R5 control metrics`

Pull requests should:

- link the governing issue
- state which phase or requirement is affected
- summarize evidence, control, or runtime impact
- include diagram or document updates when architecture meaning changes

## Security & Architecture Notes

This project is control-plane-first. Prefer changes that improve traceability, policy enforcement, provenance, and audit reconstruction over runtime complexity.
