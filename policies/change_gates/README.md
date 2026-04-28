# Change Gates

This directory contains the current PR governance gate policy.

The active policy checks:

- branch naming follows `<issue-id>/<short-name>`
- the PR body links exactly one governing issue
- the branch issue ID matches the PR issue reference
- the PR body declares the affected phase and requirements
- the required governance sections from the PR template are still present

These are the minimum policy-as-code checks for the Phase 4 PR control plane.
