from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from planner_to_unit4.application.process_budget_variance import (
    ProcessBudgetVarianceResult,
    run as run_process_budget_variance,
)
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.planning_service import PlanningService
from planner_to_unit4.infrastructure.segment_monitor import SegmentMonitor


@dataclass
class SubmitBudgetVariance:
    items_provider: BudgetVarianceItemsProvider
    planning_service: PlanningService
    segment_monitor: SegmentMonitor
    max_segment_size: int = 15000
    clock: Callable[[], datetime] = datetime.utcnow

    def run(self, pipeline_run_id: str, snapshot_path: str) -> ProcessBudgetVarianceResult:
        return run_process_budget_variance(
            items_provider=self.items_provider,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            segment_monitor=self.segment_monitor,
            max_segment_size=self.max_segment_size,
            snapshot_path=snapshot_path,
            clock=self.clock,
        )
