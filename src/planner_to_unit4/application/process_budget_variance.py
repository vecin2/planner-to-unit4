from __future__ import annotations

from dataclasses import dataclass

from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.planning_service import PlanningService


@dataclass(frozen=True)
class ProcessBudgetVarianceResult:
    pipeline_run_id: str
    status: str
    snapshot_path: str


def run(
    items_provider: BudgetVarianceItemsProvider,
    pipeline_run_id: str,
    planning_service: PlanningService,
    snapshot_path: str,
    max_segment_size: int = 15000,
) -> ProcessBudgetVarianceResult:
    items = items_provider.read_items()

    segments = list(_segment_rows(items, max_segment_size))

    for segment in segments:
        planning_service.send_segment(segment)

    return ProcessBudgetVarianceResult(
        pipeline_run_id=pipeline_run_id,
        status="COMPLETED",
        snapshot_path=snapshot_path,
    )


def _segment_rows(rows: list, segment_size: int):
    for i in range(0, len(rows), segment_size):
        yield rows[i : i + segment_size]
