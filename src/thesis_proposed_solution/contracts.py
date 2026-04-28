"""Schema contract helpers for curated and promoted data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_contract(contract_path: str | Path) -> dict[str, Any]:
    with Path(contract_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def expected_columns(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return list(contract["columns"])


def expected_column_names(contract: dict[str, Any]) -> list[str]:
    return [column["name"] for column in expected_columns(contract)]


def required_fields(contract: dict[str, Any]) -> list[str]:
    return list(contract.get("required_fields", []))


def _coerce_boolean(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError(f"Cannot coerce {value!r} to boolean")


def coerce_value(value: Any, expected_type: str) -> Any:
    if value is None:
        return None
    if expected_type == "string":
        return str(value)
    if expected_type == "integer":
        return int(value)
    if expected_type == "number":
        return float(value)
    if expected_type == "boolean":
        return _coerce_boolean(value)
    raise ValueError(f"Unsupported contract type: {expected_type}")


def coerce_record_to_contract(record: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    coerced: dict[str, Any] = {}
    for column in expected_columns(contract):
        coerced[column["name"]] = coerce_value(record.get(column["name"]), column["type"])
    return coerced


def record_matches_contract(record: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected_names = expected_column_names(contract)
    if list(record.keys()) != expected_names:
        errors.append("column order or names differ from contract")
        return False, errors

    for column in expected_columns(contract):
        name = column["name"]
        expected_type = column["type"]
        value = record.get(name)
        if value is None:
            continue
        try:
            coerced = coerce_value(value, expected_type)
        except (TypeError, ValueError):
            errors.append(f"{name} is not coercible to {expected_type}")
            continue
        if expected_type == "string" and not isinstance(coerced, str):
            errors.append(f"{name} is not a string")
        elif expected_type == "integer" and not isinstance(coerced, int):
            errors.append(f"{name} is not an integer")
        elif expected_type == "number" and not isinstance(coerced, float):
            errors.append(f"{name} is not a number")
        elif expected_type == "boolean" and not isinstance(coerced, bool):
            errors.append(f"{name} is not a boolean")
    return not errors, errors


def records_match_contract(records: list[dict[str, Any]], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for index, record in enumerate(records):
        matches, record_errors = record_matches_contract(record, contract)
        if not matches:
            errors.extend([f"row {index}: {error}" for error in record_errors])
    return not errors, errors


def required_fields_populated(records: list[dict[str, Any]], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for index, record in enumerate(records):
        for field_name in required_fields(contract):
            value = record.get(field_name)
            if value is None or value == "":
                errors.append(f"row {index}: required field {field_name} is null")
    return not errors, errors
