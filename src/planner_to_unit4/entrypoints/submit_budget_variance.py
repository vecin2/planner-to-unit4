from __future__ import annotations

from typing import Any
from typing import Callable

from planner_to_unit4.application.submit_budget_variance import SubmitBudgetVariance
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.spark_budget_variance_reader import (
    SparkBudgetVarianceReader,
)
from planner_to_unit4.infrastructure.retrying_planning_service import (
    RetryingPlanningService,
)
from planner_to_unit4.infrastructure.spark_segment_monitor import SparkSegmentMonitor
from planner_to_unit4.infrastructure.soap_planning_service import SoapPlanningService


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
    "segment_monitor_retention_days": None,
    "timeout": 90,
    "report_max_sample_rows": 10,
    "artifact_save_mode": "on_failure",
    "soap_retry_retries": 0,
}

ALLOWED_KEYS = REQUIRED_KEYS | set(OPTIONAL_DEFAULTS.keys())


def main(
    *,
    spark,
    config: dict[str, object],
    log_fn: Callable[[str], None],
    budget_variance_rows_filter: Callable[[Any], Any] | None = None,
    artifact_fs: Any | None = None,
) -> SubmitBudgetVariance:
    """Create a configured budget-variance submitter.

    The submitter `run(...)` method returns a standardized outcome object with
    `status` (`COMPLETED` or `FAILED`) and a `to_payload()` method for
    notebook-to-pipeline handoff.

    Runtime arguments (not part of ``config``):
    - ``spark``: Spark session used for table reads and monitor writes.
    - ``log_fn``: callable used to emit operational logs.
    - ``budget_variance_rows_filter``: optional callable that receives a Spark
      DataFrame and must return a Spark DataFrame. If omitted, rows are ordered
      by ``record_no``.
    - ``artifact_fs``: optional filesystem object with ``mkdirs`` and
      ``put`` methods. Artifact write behavior is controlled by
      ``artifact_save_mode`` for request/report artifacts.

    Config keys (validated by ``validate_config``):
    Required
    - ``source_table_name`` (str)
    - ``version`` (str)
    - ``batch`` (str)
    - ``endpoint`` (str)
    - ``username`` (str): integration username used for SOAP authentication.
    - ``client`` (str): authentication client context for the user (``bi`` or ``c1``).
    - ``password`` (str): integration user password used for SOAP authentication.
    - ``segment_monitoring_table`` (str)

    Optional
    - ``max_segment_size`` (int, default ``12000``)
    - ``timeout`` (int, default ``90``)
    - ``segment_monitor_retention_days`` (int | None, default ``None``)
    - ``report_max_sample_rows`` (int, default ``10``)
    - ``artifact_save_mode`` (str, default ``on_failure``; allowed
      ``on_failure``, ``always``, ``never``)
    - ``soap_retry_retries`` (int, default ``0``; retries on exceptions)
    """
    import requests

    validated = validate_config(config)
    log_fn(
        _format_submitter_config_log(
            validated=validated,
            artifact_fs_enabled=artifact_fs is not None,
            rows_filter_enabled=budget_variance_rows_filter is not None,
        )
    )
    reader = SparkBudgetVarianceReader(
        spark=spark,
        table_name=validated["source_table_name"],
        rows_filter=budget_variance_rows_filter,
    )
    items_provider = BudgetVarianceItemsProvider(
        reader=reader,
        version=validated["version"],
        batch=validated["batch"],
    )
    base_planning_service = SoapPlanningService(
        endpoint=validated["endpoint"],
        username=validated["username"],
        client=validated["client"],
        password=validated["password"],
        http_post=requests.post,
        timeout=validated["timeout"],
        log_fn=log_fn,
    )
    planning_service = RetryingPlanningService(
        service=base_planning_service,
        retries=validated["soap_retry_retries"],
        log_fn=log_fn,
    )
    segment_monitor = SparkSegmentMonitor(
        spark=spark,
        table_name=validated["segment_monitoring_table"],
    )
    return SubmitBudgetVariance(
        items_provider=items_provider,
        planning_service=planning_service,
        segment_monitor=segment_monitor,
        log_fn=log_fn,
        max_segment_size=validated["max_segment_size"],
        segment_monitor_retention_days=validated["segment_monitor_retention_days"],
        report_max_sample_rows=validated["report_max_sample_rows"],
        artifact_save_mode=validated["artifact_save_mode"],
        artifact_fs=artifact_fs,
    )


def validate_config(config: dict[str, object]) -> dict[str, object]:
    """Validate submitter configuration.

    Validation rules:
    - unknown keys are rejected
    - missing required keys are rejected
    - required keys must be strings
    - ``max_segment_size`` and ``timeout`` must be integers > 0
    - ``report_max_sample_rows`` must be integer > 0
    - ``segment_monitor_retention_days`` is optional and must be integer > 0
    - ``artifact_save_mode`` must be one of ``on_failure``, ``always``, ``never``
    - ``soap_retry_retries`` must be integer >= 0

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

    report_max_sample_rows = config.get(
        "report_max_sample_rows",
        OPTIONAL_DEFAULTS["report_max_sample_rows"],
    )
    if not _is_int(report_max_sample_rows):
        invalid_types["report_max_sample_rows"] = type(report_max_sample_rows).__name__
    elif report_max_sample_rows <= 0:
        invalid_ranges["report_max_sample_rows"] = report_max_sample_rows

    segment_monitor_retention_days = config.get(
        "segment_monitor_retention_days",
        OPTIONAL_DEFAULTS["segment_monitor_retention_days"],
    )
    if segment_monitor_retention_days is not None:
        if not _is_int(segment_monitor_retention_days):
            invalid_types["segment_monitor_retention_days"] = type(
                segment_monitor_retention_days
            ).__name__
        elif segment_monitor_retention_days <= 0:
            invalid_ranges["segment_monitor_retention_days"] = segment_monitor_retention_days

    artifact_save_mode = config.get(
        "artifact_save_mode",
        OPTIONAL_DEFAULTS["artifact_save_mode"],
    )
    if not isinstance(artifact_save_mode, str):
        invalid_types["artifact_save_mode"] = type(artifact_save_mode).__name__
    elif artifact_save_mode not in {"on_failure", "always", "never"}:
        invalid_values["artifact_save_mode"] = artifact_save_mode

    soap_retry_retries = config.get(
        "soap_retry_retries",
        OPTIONAL_DEFAULTS["soap_retry_retries"],
    )
    if not _is_int(soap_retry_retries):
        invalid_types["soap_retry_retries"] = type(soap_retry_retries).__name__
    elif soap_retry_retries < 0:
        invalid_ranges["soap_retry_retries"] = soap_retry_retries

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
        "source_table_name": config["source_table_name"],
        "version": config["version"],
        "batch": config["batch"],
        "endpoint": config["endpoint"],
        "username": config["username"],
        "client": config["client"],
        "password": config["password"],
        "segment_monitoring_table": config["segment_monitoring_table"],
        "max_segment_size": max_segment_size,
        "segment_monitor_retention_days": segment_monitor_retention_days,
        "timeout": timeout,
        "report_max_sample_rows": report_max_sample_rows,
        "artifact_save_mode": artifact_save_mode,
        "soap_retry_retries": soap_retry_retries,
    }


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _format_submitter_config_log(
    *,
    validated: dict[str, object],
    artifact_fs_enabled: bool,
    rows_filter_enabled: bool,
) -> str:
    redacted = dict(validated)
    redacted["password"] = "***"
    config_items = ", ".join(
        f"{key}={redacted[key]!r}" for key in sorted(redacted)
    )
    return (
        "Configured budget variance submitter: "
        f"{config_items}, "
        f"artifact_fs_enabled={artifact_fs_enabled}, "
        f"rows_filter_enabled={rows_filter_enabled}"
    )
