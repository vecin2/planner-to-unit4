from __future__ import annotations

from typing import Any

REQUIRED_KEYS = {
    "source_table_name",
    "version",
    "batch",
    "endpoint",
    "username",
    "client",
    "password",
    "segment_monitoring_table",
}

OPTIONAL_DEFAULTS: dict[str, Any] = {
    "max_segment_size": 12000,
    "max_records": None,
    "timeout": 90,
}

ALLOWED_KEYS = REQUIRED_KEYS | set(OPTIONAL_DEFAULTS.keys())


def validate_config(config: dict[str, object]) -> dict[str, object]:
    missing_keys = sorted(REQUIRED_KEYS - config.keys())
    unknown_keys = sorted(set(config.keys()) - ALLOWED_KEYS)
    invalid_types: dict[str, str] = {}
    invalid_ranges: dict[str, object] = {}

    for key in sorted(REQUIRED_KEYS):
        if key not in config:
            continue
        value = config[key]
        if not isinstance(value, str):
            invalid_types[key] = type(value).__name__

    max_segment_size = config.get("max_segment_size", OPTIONAL_DEFAULTS["max_segment_size"])
    if not _is_int(max_segment_size):
        invalid_types["max_segment_size"] = type(max_segment_size).__name__
    elif max_segment_size <= 0:
        invalid_ranges["max_segment_size"] = max_segment_size

    timeout = config.get("timeout", OPTIONAL_DEFAULTS["timeout"])
    if not _is_int(timeout):
        invalid_types["timeout"] = type(timeout).__name__
    elif timeout <= 0:
        invalid_ranges["timeout"] = timeout

    max_records = config.get("max_records", OPTIONAL_DEFAULTS["max_records"])
    if max_records is not None:
        if not _is_int(max_records):
            invalid_types["max_records"] = type(max_records).__name__
        elif max_records <= 0:
            invalid_ranges["max_records"] = max_records

    if missing_keys or unknown_keys or invalid_types or invalid_ranges:
        raise ValueError(
            "Invalid config: "
            f"missing keys={missing_keys}; "
            f"unknown keys={unknown_keys}; "
            f"invalid types={invalid_types}; "
            f"invalid ranges={invalid_ranges}"
        )

    return {
        "source_table_name": config["source_table_name"],
        "version": config["version"],
        "batch": config["batch"],
        "endpoint": config["endpoint"],
        "username": config["username"],
        "client": config["client"],
        "password": config["password"],
        "segment_monitoring_table": config["segment_monitoring_table"],
        "max_segment_size": max_segment_size,
        "max_records": max_records,
        "timeout": timeout,
    }


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
