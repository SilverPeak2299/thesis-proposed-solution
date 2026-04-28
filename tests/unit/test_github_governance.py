from __future__ import annotations

from thesis_proposed_solution.github_governance import (
    build_pr_governance_input,
    extract_issue_references,
    parse_branch_name,
    parse_phase,
    parse_requirements,
)


def test_extract_issue_references_preserves_unique_order() -> None:
    issue_ids = extract_issue_references("Implements #42 and references #7 before #42 again.")

    assert issue_ids == ["42", "7"]


def test_parse_branch_name_accepts_governed_pattern() -> None:
    branch = parse_branch_name("42/add-governance-pipeline")

    assert branch == {
        "name": "42/add-governance-pipeline",
        "valid": True,
        "issue_id": "42",
    }


def test_parse_phase_and_requirements_from_pr_template_body() -> None:
    body = """
## Requirements / Phase

- Phase: `Phase 4`
- Requirements: `R1, R4, R5`
"""

    assert parse_phase(body) == "Phase 4"
    assert parse_requirements(body) == ["R1", "R4", "R5"]


def test_build_pr_governance_input_captures_linked_issue_and_template_sections() -> None:
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 12,
            "title": "Add governed PR checks",
            "draft": False,
            "body": """
## Summary

Adds PR controls.

## Governing Issue

- Issue: `#42`
- Branch: `42/add-governed-pr-checks`

## Requirements / Phase

- Phase: `Phase 4`
- Requirements: `R1, R4`

## Impact

- Evidence impact: Adds governance evidence.
- Control impact: Adds PR checks.
- Runtime impact: None.

## Validation

- Docs reviewed: yes
- Commands run: pytest
- Follow-up work: release controls
""",
            "head": {"ref": "42/add-governed-pr-checks"},
            "base": {"ref": "main"},
            "labels": [{"name": "change-request"}],
        },
    }

    governance_input = build_pr_governance_input(payload)

    assert governance_input["pull_request"]["head_ref"] == "42/add-governed-pr-checks"
    assert governance_input["governance"]["branch_name_valid"] is True
    assert governance_input["governance"]["branch_issue_id"] == "42"
    assert governance_input["governance"]["linked_issue_id"] == "42"
    assert governance_input["governance"]["phase"] == "Phase 4"
    assert governance_input["governance"]["requirements"] == ["R1", "R4"]
    assert all(governance_input["governance"]["template_sections"].values())
