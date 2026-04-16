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


@dataclass
class SubmitBudgetVariance:
    items_provider: BudgetVarianceItemsProvider
    planning_service: PlanningService
    segment_monitor: SegmentMonitor
    log_fn: Callable[[str], None]
    max_segment_size: int = 15000
    clock: Callable[[], datetime] = datetime.utcnow

    def run(self, pipeline_run_id: str, snapshot_path: str) -> ProcessBudgetVarianceResult:
        items = self.items_provider.read_items()

        segments = list(_segment_rows(items, self.max_segment_size))
        self.log_fn(
            "Starting budget variance submission: "
            f"pipeline_run_id={pipeline_run_id} snapshot_path={snapshot_path} "
            f"items={len(items)} segments={len(segments)} max_segment_size={self.max_segment_size}"
        )

        failed_segments = 0

        for segment_index, segment in enumerate(segments, start=1):
            self.log_fn(f"Submitting segment {segment_index}/{len(segments)} size={len(segment)}")
            try:
                result = self.planning_service.send_segment(segment)
            except Exception as exc:  # noqa: BLE001 - boundary IO failure
                self.segment_monitor.record_failed(
                    pipeline_run_id=pipeline_run_id,
                    snapshot_path=snapshot_path,
                    segment_index=segment_index,
                    segment_size=len(segment),
                    http_status=None,
                    message=str(exc),
                    submitted_at_utc=self.clock(),
                )
                self.log_fn(f"Recorded failed segment: segment_index={segment_index} error={exc}")
                raise

            order_no = result.get("order_no")
            self.log_fn(
                "Segment response: "
                f"segment_index={segment_index} http_status={result.get('http_status')} "
                f"order_no={order_no} message={result.get('message')}"
            )
            failed_segments += _record_segment_result(
                segment_monitor=self.segment_monitor,
                log_fn=self.log_fn,
                pipeline_run_id=pipeline_run_id,
                snapshot_path=snapshot_path,
                segment_index=segment_index,
                segment_size=len(segment),
                order_no=order_no,
                http_status=result.get("http_status"),
                message=result.get("message"),
                submitted_at_utc=self.clock(),
            )

        self.log_fn(
            "Completed budget variance submission: "
            f"pipeline_run_id={pipeline_run_id} snapshot_path={snapshot_path}"
        )
        if failed_segments:
            raise RuntimeError(f"Budget variance submission failed for {failed_segments} segments")
        return ProcessBudgetVarianceResult(
            pipeline_run_id=pipeline_run_id,
            status="COMPLETED",
            snapshot_path=snapshot_path,
        )


def _segment_rows(rows: list, segment_size: int):
    for i in range(0, len(rows), segment_size):
        yield rows[i : i + segment_size]


def _record_segment_result(
    *,
    segment_monitor: SegmentMonitor,
    log_fn: Callable[[str], None],
    pipeline_run_id: str,
    snapshot_path: str,
    segment_index: int,
    segment_size: int,
    order_no: str | None,
    http_status: int | None,
    message: str | None,
    submitted_at_utc: datetime,
) -> int:
    if order_no is None:
        segment_monitor.record_failed(
            pipeline_run_id=pipeline_run_id,
            snapshot_path=snapshot_path,
            segment_index=segment_index,
            segment_size=segment_size,
            http_status=http_status,
            message=message,
            submitted_at_utc=submitted_at_utc,
        )
        log_fn(f"Recorded failed segment: segment_index={segment_index} http_status={http_status}")
        return 1

    segment_monitor.record_submitted(
        pipeline_run_id=pipeline_run_id,
        snapshot_path=snapshot_path,
        segment_index=segment_index,
        segment_size=segment_size,
        order_no=order_no,
        http_status=http_status,
        message=message,
        submitted_at_utc=submitted_at_utc,
    )
    log_fn(f"Recorded submitted segment: segment_index={segment_index} order_no={order_no}")
    return 0
