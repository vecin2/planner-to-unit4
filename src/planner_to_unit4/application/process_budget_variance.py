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
    log_fn: Callable[[str], None],
    snapshot_path: str,
    max_segment_size: int = 15000,
    clock: Callable[[], datetime] = datetime.utcnow,
) -> ProcessBudgetVarianceResult:
    items = items_provider.read_items()

    segments = list(_segment_rows(items, max_segment_size))
    log_fn(
        "Starting budget variance submission: "
        f"pipeline_run_id={pipeline_run_id} snapshot_path={snapshot_path} "
        f"items={len(items)} segments={len(segments)} max_segment_size={max_segment_size}"
    )

    for segment_index, segment in enumerate(segments, start=1):
        log_fn(f"Submitting segment {segment_index}/{len(segments)} size={len(segment)}")
        result = planning_service.send_segment(segment)
        order_no = result.get("order_no")
        log_fn(
            "Segment response: "
            f"segment_index={segment_index} http_status={result.get('http_status')} "
            f"order_no={order_no} message={result.get('message')}"
        )
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
            log_fn(f"Recorded submitted segment: segment_index={segment_index} order_no={order_no}")

    log_fn(
        "Completed budget variance submission: "
        f"pipeline_run_id={pipeline_run_id} snapshot_path={snapshot_path}"
    )
    return ProcessBudgetVarianceResult(
        pipeline_run_id=pipeline_run_id,
        status="COMPLETED",
        snapshot_path=snapshot_path,
    )


def _segment_rows(rows: list, segment_size: int):
    for i in range(0, len(rows), segment_size):
        yield rows[i : i + segment_size]
