from __future__ import annotations

from dataclasses import dataclass

import requests

from planner_to_unit4.application.budget_variance_items_provider import (
    DefaultBudgetVarianceItemsProvider,
)
from planner_to_unit4.application.process_budget_variance import (
    ProcessBudgetVarianceResult,
    run as run_process_budget_variance,
)
from planner_to_unit4.infrastructure.budget_variance_reader import BudgetVarianceReader
from planner_to_unit4.infrastructure.planning_service import PlanningService
from planner_to_unit4.infrastructure.spark_budget_variance_reader import (
    SparkBudgetVarianceReader,
)
from planner_to_unit4.infrastructure.soap_planning_service import SoapPlanningService


@dataclass
class ProcessBudgetVarianceApp:
    items_provider: DefaultBudgetVarianceItemsProvider
    planning_service: PlanningService
    max_batch_size: int = 15000
    snapshot_path: str | None = None

    def run(self, pipeline_run_id: str) -> ProcessBudgetVarianceResult:
        return run_process_budget_variance(
            items_provider=self.items_provider,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            max_batch_size=self.max_batch_size,
            snapshot_path=self.snapshot_path,
        )


def build_process_budget_variance_app(
    *,
    spark,
    table_name: str,
    endpoint: str,
    username: str,
    client: str,
    password: str,
    version: str,
    batch: str,
    max_batch_size: int = 15000,
    snapshot_path: str | None = None,
    timeout: int = 60,
) -> ProcessBudgetVarianceApp:
    reader = SparkBudgetVarianceReader(spark=spark, table_name=table_name)
    return build_process_budget_variance_app_with_reader(
        reader=reader,
        endpoint=endpoint,
        username=username,
        client=client,
        password=password,
        version=version,
        batch=batch,
        max_batch_size=max_batch_size,
        snapshot_path=snapshot_path,
        timeout=timeout,
    )


def build_process_budget_variance_app_with_reader(
    *,
    reader: BudgetVarianceReader,
    endpoint: str,
    username: str,
    client: str,
    password: str,
    version: str,
    batch: str,
    max_batch_size: int = 15000,
    snapshot_path: str | None = None,
    timeout: int = 60,
) -> ProcessBudgetVarianceApp:
    items_provider = DefaultBudgetVarianceItemsProvider(
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
    return ProcessBudgetVarianceApp(
        items_provider=items_provider,
        planning_service=planning_service,
        max_batch_size=max_batch_size,
        snapshot_path=snapshot_path,
    )
