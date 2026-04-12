from __future__ import annotations

from planner_to_unit4.application.submit_budget_variance import SubmitBudgetVariance
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
    source_table_name: str,
    version: str,
    batch: str,
    max_records: int | None = None,
    endpoint: str,
    username: str,
    client: str,
    password: str,
    max_segment_size: int = 15000,
    timeout: int = 60,
    segment_monitoring_table: str = "planner_to_unit4.segment_monitoring",
) -> SubmitBudgetVariance:
    import requests

    reader = SparkBudgetVarianceReader(
        spark=spark,
        table_name=source_table_name,
        max_records=max_records,
    )
    items_provider = BudgetVarianceItemsProvider(
        reader=reader,
        version=version,
        batch=batch,
    )
    planning_service = SoapPlanningService(
        endpoint=endpoint,
        username=username,
        client=client,
        password=password,
        http_post=requests.post,
        timeout=timeout,
    )
    segment_monitor = SparkSegmentMonitor(
        spark=spark,
        table_name=segment_monitoring_table,
    )
    return SubmitBudgetVariance(
        items_provider=items_provider,
        planning_service=planning_service,
        segment_monitor=segment_monitor,
        max_segment_size=max_segment_size,
    )
