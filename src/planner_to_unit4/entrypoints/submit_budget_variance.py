from __future__ import annotations

from typing import Callable

from planner_to_unit4.application.submit_budget_variance import SubmitBudgetVariance
from planner_to_unit4.entrypoints.submit_budget_variance_config import validate_config
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.spark_budget_variance_reader import (
    SparkBudgetVarianceReader,
)
from planner_to_unit4.infrastructure.soap_planning_service import SoapPlanningService
from planner_to_unit4.infrastructure.spark_segment_monitor import SparkSegmentMonitor


def main(
    *,
    spark,
    config: dict[str, object],
    log_fn: Callable[[str], None],
) -> SubmitBudgetVariance:
    import requests

    validated = validate_config(config)
    reader = SparkBudgetVarianceReader(
        spark=spark,
        table_name=validated["source_table_name"],
        max_records=validated["max_records"],
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
    )
