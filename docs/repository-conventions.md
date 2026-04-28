# Repository Conventions

## Branches

Governed changes use the branch pattern:

- `<issue-id>/<short-name>`

Example:

- `123/add-release-manifest`

## Pull Requests

Every PR should include:

- a linked governing issue
- the affected stage or requirements
- a short note on evidence, control, and runtime impact

## Ownership

Stage 1 uses a single current owner in `CODEOWNERS`, but the repository is
structured so code-owner and data-owner approval boundaries can split later.

## Control-Plane Priority

If a change affects architecture meaning, evidence flow, or control intent,
update the relevant documentation in `docs/` alongside the code or scaffold
change.
