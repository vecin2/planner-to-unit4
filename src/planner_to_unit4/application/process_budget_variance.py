from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.planning_service import PlanningService
from planner_to_unit4.infrastructure.segment_monitor import SegmentMonitor


@dataclass(frozen=True)
class ProcessBudgetVarianceResult:
    pipeline_run_id: str
    status: str
    snapshot_path: str


def run(
    items_provider: BudgetVarianceItemsProvider,
    pipeline_run_id: str,
    planning_service: PlanningService,
    segment_monitor: SegmentMonitor,
    snapshot_path: str,
    max_segment_size: int = 15000,
    clock: Callable[[], datetime] = datetime.utcnow,
) -> ProcessBudgetVarianceResult:
    items = items_provider.read_items()

    segments = list(_segment_rows(items, max_segment_size))

    for segment_index, segment in enumerate(segments, start=1):
        result = planning_service.send_segment(segment)
        order_no = result.get("order_no")
        if order_no:
            segment_monitor.record_submitted(
                pipeline_run_id=pipeline_run_id,
                snapshot_path=snapshot_path,
                segment_index=segment_index,
                segment_size=len(segment),
                order_no=order_no,
                http_status=result.get("http_status"),
                message=result.get("message"),
                submitted_at_utc=clock(),
            )

    return ProcessBudgetVarianceResult(
        pipeline_run_id=pipeline_run_id,
        status="COMPLETED",
        snapshot_path=snapshot_path,
    )


def _segment_rows(rows: list, segment_size: int):
    for i in range(0, len(rows), segment_size):
        yield rows[i : i + segment_size]
