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
}

ALLOWED_KEYS = REQUIRED_KEYS | set(OPTIONAL_DEFAULTS.keys())


def main(
    *,
    spark,
    config: dict[str, object],
    log_fn: Callable[[str], None],
    budget_variance_rows_filter: Callable[[Any], Any] | None = None,
    failed_request_fs: Any | None = None,
) -> SubmitBudgetVariance:
    import requests

    validated = validate_config(config)
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
    planning_service = SoapPlanningService(
        endpoint=validated["endpoint"],
        username=validated["username"],
        client=validated["client"],
        password=validated["password"],
        http_post=requests.post,
        timeout=validated["timeout"],
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
        failed_request_fs=failed_request_fs,
    )


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
        "segment_monitor_retention_days": segment_monitor_retention_days,
        "timeout": timeout,
    }


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
