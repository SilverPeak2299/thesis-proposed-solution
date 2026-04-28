"""Helpers for building PR governance inputs for CI policy checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

BRANCH_NAME_PATTERN = re.compile(r"^(?P<issue_id>\d+)\/[a-z0-9][a-z0-9-]*$")
ISSUE_REFERENCE_PATTERN = re.compile(r"#(?P<issue_id>\d+)\b")
PHASE_PATTERN = re.compile(r"^- Phase:\s*`?(?P<phase>[^`\n]+?)`?\s*$", re.MULTILINE)
REQUIREMENTS_PATTERN = re.compile(
    r"^- Requirements:\s*`?(?P<requirements>[^`\n]+?)`?\s*$",
    re.MULTILINE,
)


def extract_issue_references(text: str) -> list[str]:
    seen: set[str] = set()
    issue_ids: list[str] = []
    for match in ISSUE_REFERENCE_PATTERN.finditer(text):
        issue_id = match.group("issue_id")
        if issue_id not in seen:
            seen.add(issue_id)
            issue_ids.append(issue_id)
    return issue_ids


def parse_branch_name(branch_name: str) -> dict[str, Any]:
    match = BRANCH_NAME_PATTERN.fullmatch(branch_name)
    return {
        "name": branch_name,
        "valid": match is not None,
        "issue_id": match.group("issue_id") if match else None,
    }


def parse_phase(text: str) -> str | None:
    match = PHASE_PATTERN.search(text)
    if match is None:
        return None
    return match.group("phase").strip()


def parse_requirements(text: str) -> list[str]:
    match = REQUIREMENTS_PATTERN.search(text)
    if match is None:
        return []

    requirements: list[str] = []
    seen: set[str] = set()
    for token in match.group("requirements").split(","):
        normalized = token.strip().strip("`")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        requirements.append(normalized)
    return requirements


def template_section_presence(text: str) -> dict[str, bool]:
    return {
        "summary": "## Summary" in text,
        "governing_issue": "## Governing Issue" in text,
        "requirements_phase": "## Requirements / Phase" in text,
        "impact": "## Impact" in text,
        "validation": "## Validation" in text,
    }


def build_pr_governance_input(event_payload: Mapping[str, Any]) -> dict[str, Any]:
    pull_request = dict(event_payload.get("pull_request") or {})
    body = pull_request.get("body") or ""
    branch = parse_branch_name(str(pull_request.get("head", {}).get("ref") or ""))
    issue_references = extract_issue_references(body)
    linked_issue_id = issue_references[0] if len(issue_references) == 1 else None

    return {
        "event_name": event_payload.get("action"),
        "pull_request": {
            "number": pull_request.get("number"),
            "title": pull_request.get("title"),
            "draft": bool(pull_request.get("draft", False)),
            "base_ref": pull_request.get("base", {}).get("ref"),
            "head_ref": pull_request.get("head", {}).get("ref"),
            "labels": [label.get("name") for label in pull_request.get("labels", [])],
        },
        "governance": {
            "branch_name": branch["name"],
            "branch_issue_id": branch["issue_id"],
            "branch_name_valid": branch["valid"],
            "issue_references": issue_references,
            "linked_issue_id": linked_issue_id,
            "phase": parse_phase(body),
            "requirements": parse_requirements(body),
            "template_sections": template_section_presence(body),
        },
    }


def load_event_payload(event_path: str | Path) -> dict[str, Any]:
    with Path(event_path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("GitHub event payload must be a JSON object")
    return payload
