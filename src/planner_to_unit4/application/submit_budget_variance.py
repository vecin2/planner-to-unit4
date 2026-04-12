from __future__ import annotations

from dataclasses import dataclass

from planner_to_unit4.application.process_budget_variance import (
    ProcessBudgetVarianceResult,
    run as run_process_budget_variance,
)
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.planning_service import PlanningService


@dataclass
class SubmitBudgetVariance:
    items_provider: BudgetVarianceItemsProvider
    planning_service: PlanningService
    max_segment_size: int = 15000

    def run(self, pipeline_run_id: str, snapshot_path: str) -> ProcessBudgetVarianceResult:
        return run_process_budget_variance(
            items_provider=self.items_provider,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            max_segment_size=self.max_segment_size,
            snapshot_path=snapshot_path,
        )
