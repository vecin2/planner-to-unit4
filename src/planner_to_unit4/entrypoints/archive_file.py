from __future__ import annotations

from typing import Any
from typing import Callable

from planner_to_unit4.application.archive_file import ArchiveFile

REQUIRED_KEYS = {
    "archive_root_path",
}

OPTIONAL_DEFAULTS: dict[str, Any] = {
    "archive_retention_days": None,
}

ALLOWED_KEYS = REQUIRED_KEYS | set(OPTIONAL_DEFAULTS.keys())


def main(
    *,
    fs,
    config: dict[str, object],
    log_fn: Callable[[str], None],
) -> ArchiveFile:
    """Create a configured file archiver.

    The archiver `run(...)` method returns a standardized outcome object with
    `status` (`COMPLETED` or `FAILED`) and a `to_payload()` method for
    notebook-to-pipeline handoff.

    Runtime arguments (not part of ``config``):
    - ``fs``: filesystem object used for ``mkdirs``, ``mv``, ``ls``, ``rm``.
    - ``log_fn``: callable used to emit operational logs.

    Config keys (validated by ``validate_config``):
    Required
    - ``archive_root_path`` (str)

    Optional
    - ``archive_retention_days`` (int | None, default ``None``)
    """
    validated = validate_config(config)
    return ArchiveFile(
        fs=fs,
        archive_root_path=validated["archive_root_path"],
        archive_retention_days=validated["archive_retention_days"],
        log_fn=log_fn,
    )


def validate_config(config: dict[str, object]) -> dict[str, object]:
    """Validate archive configuration.

    Validation rules:
    - unknown keys are rejected
    - missing required keys are rejected
    - required keys must be strings
    - ``archive_retention_days`` is optional and must be integer > 0

    Raises ``ValueError`` with a structured summary when validation fails.
    """
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

    archive_retention_days = config.get(
        "archive_retention_days",
        OPTIONAL_DEFAULTS["archive_retention_days"],
    )
    if archive_retention_days is not None:
        if not _is_int(archive_retention_days):
            invalid_types["archive_retention_days"] = type(archive_retention_days).__name__
        elif archive_retention_days <= 0:
            invalid_ranges["archive_retention_days"] = archive_retention_days

    if missing_keys or unknown_keys or invalid_types or invalid_ranges:
        raise ValueError(
            "Invalid config: "
            f"missing keys={missing_keys}; "
            f"unknown keys={unknown_keys}; "
            f"invalid types={invalid_types}; "
            f"invalid ranges={invalid_ranges}"
        )

    return {
        "archive_root_path": config["archive_root_path"],
        "archive_retention_days": archive_retention_days,
    }


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
