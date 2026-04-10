from __future__ import annotations

from dataclasses import dataclass

import requests

from planner_to_unit4.application.process_budget_variance import (
    ProcessBudgetVarianceResult,
    run as run_process_budget_variance,
)
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.planning_service import PlanningService
from planner_to_unit4.infrastructure.spark_budget_variance_reader import (
    SparkBudgetVarianceReader,
)
from planner_to_unit4.infrastructure.soap_planning_service import SoapPlanningService


@dataclass
class BudgetVarianceProcessor:
    items_provider: BudgetVarianceItemsProvider
    planning_service: PlanningService
    max_batch_size: int = 15000

    def run(self, pipeline_run_id: str, snapshot_path: str) -> ProcessBudgetVarianceResult:
        return run_process_budget_variance(
            items_provider=self.items_provider,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            max_batch_size=self.max_batch_size,
            snapshot_path=snapshot_path,
        )

    @classmethod
    def make_from(
        cls,
        spark,
        source_table_name: str,
        version: str,
        batch: str,
        endpoint: str,
        username: str,
        client: str,
        password: str,
        max_batch_size: int = 15000,
        timeout: int = 60,
    ) -> "BudgetVarianceProcessor":
        reader = SparkBudgetVarianceReader(spark=spark, table_name=source_table_name)
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
        return cls(
            items_provider=items_provider,
            planning_service=planning_service,
            max_batch_size=max_batch_size,
        )
