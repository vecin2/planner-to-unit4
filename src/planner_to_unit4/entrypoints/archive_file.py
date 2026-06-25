from __future__ import annotations

from typing import Any
from typing import Callable

from planner_to_unit4.application.archive_file import ArchiveFile

REQUIRED_KEYS = {
    "archive_root_path",
}

OPTIONAL_DEFAULTS: dict[str, Any] = {
    "archive_retention_days": None,
    "archive_write_mode": "copy",
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
    - ``fs``: filesystem object used for ``mkdirs``, ``cp``, ``mv``, ``ls``, ``rm``.
    - ``log_fn``: callable used to emit operational logs.

    Config keys (validated by ``validate_config``):
    Required
    - ``archive_root_path`` (str)

    Optional
    - ``archive_retention_days`` (int | None, default ``None``)
    - ``archive_write_mode`` (str, default ``copy``; allowed ``copy`` or ``move``)
    """
    validated = validate_config(config)
    return ArchiveFile(
        fs=fs,
        archive_root_path=validated["archive_root_path"],
        archive_retention_days=validated["archive_retention_days"],
        archive_write_mode=validated["archive_write_mode"],
        log_fn=log_fn,
    )


def validate_config(config: dict[str, object]) -> dict[str, object]:
    """Validate archive configuration.

    Validation rules:
    - unknown keys are rejected
    - missing required keys are rejected
    - required keys must be strings
    - ``archive_retention_days`` is optional and must be integer > 0
    - ``archive_write_mode`` must be one of ``copy`` or ``move``

    Raises ``ValueError`` with a structured summary when validation fails.
    """
    missing_keys = sorted(REQUIRED_KEYS - config.keys())
    unknown_keys = sorted(set(config.keys()) - ALLOWED_KEYS)
    invalid_types: dict[str, str] = {}
    invalid_ranges: dict[str, object] = {}
    invalid_values: dict[str, object] = {}

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

    archive_write_mode = config.get(
        "archive_write_mode",
        OPTIONAL_DEFAULTS["archive_write_mode"],
    )
    if not isinstance(archive_write_mode, str):
        invalid_types["archive_write_mode"] = type(archive_write_mode).__name__
    elif archive_write_mode not in {"copy", "move"}:
        invalid_values["archive_write_mode"] = archive_write_mode

    if missing_keys or unknown_keys or invalid_types or invalid_ranges or invalid_values:
        raise ValueError(
            "Invalid config: "
            f"missing keys={missing_keys}; "
            f"unknown keys={unknown_keys}; "
            f"invalid types={invalid_types}; "
            f"invalid ranges={invalid_ranges}; "
            f"invalid values={invalid_values}"
        )

    return {
        "archive_root_path": config["archive_root_path"],
        "archive_retention_days": archive_retention_days,
        "archive_write_mode": archive_write_mode,
    }


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
