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


@dataclass(frozen=True)
class SegmentFailureDetail:
    segment_index: int
    http_status: int | None
    message: str | None


@dataclass
class SubmitBudgetVariance:
    items_provider: BudgetVarianceItemsProvider
    planning_service: PlanningService
    segment_monitor: SegmentMonitor
    log_fn: Callable[[str], None]
    max_segment_size: int = 15000
    segment_monitor_retention_days: int | None = None
    clock: Callable[[], datetime] = datetime.utcnow

    def run(self, pipeline_run_id: str, snapshot_path: str) -> ProcessBudgetVarianceResult:
        if self.segment_monitor_retention_days is not None:
            try:
                self.segment_monitor.apply_retention(
                    retention_days=self.segment_monitor_retention_days,
                    now_utc=self.clock(),
                )
            except Exception as exc:  # noqa: BLE001 - retention should not block submission
                self.log_fn(
                    "Retention cleanup warning: "
                    f"retention_days={self.segment_monitor_retention_days} error={exc}"
                )

        items = self.items_provider.read_items()

        segments = list(_segment_rows(items, self.max_segment_size))
        self.log_fn(
            "Starting budget variance submission: "
            f"pipeline_run_id={pipeline_run_id} snapshot_path={snapshot_path} "
            f"items={len(items)} segments={len(segments)} max_segment_size={self.max_segment_size}"
        )

        failure_details: list[SegmentFailureDetail] = []

        for segment_index, segment in enumerate(segments, start=1):
            self.log_fn(f"Submitting segment {segment_index}/{len(segments)} size={len(segment)}")
            try:
                result = self.planning_service.send_segment(segment)
            except Exception as exc:  # noqa: BLE001 - boundary IO failure
                failure_detail = SegmentFailureDetail(
                    segment_index=segment_index,
                    http_status=None,
                    message=str(exc),
                )
                failure_details.append(failure_detail)
                self.segment_monitor.record_failed(
                    pipeline_run_id=pipeline_run_id,
                    snapshot_path=snapshot_path,
                    segment_index=segment_index,
                    segment_size=len(segment),
                    http_status=failure_detail.http_status,
                    message=failure_detail.message,
                    submitted_at_utc=self.clock(),
                )
                self.log_fn(f"Recorded failed segment: segment_index={segment_index} error={exc}")
                raise RuntimeError(
                    _build_failure_summary(
                        pipeline_run_id=pipeline_run_id,
                        failure_details=failure_details,
                    )
                ) from exc

            order_no = result.get("order_no")
            self.log_fn(
                "Segment response: "
                f"segment_index={segment_index} http_status={result.get('http_status')} "
                f"order_no={order_no} message={result.get('message')}"
            )
            failure_detail = _record_segment_result(
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
            if failure_detail is not None:
                failure_details.append(failure_detail)

        self.log_fn(
            "Completed budget variance submission: "
            f"pipeline_run_id={pipeline_run_id} snapshot_path={snapshot_path}"
        )
        if failure_details:
            raise RuntimeError(
                _build_failure_summary(
                    pipeline_run_id=pipeline_run_id,
                    failure_details=failure_details,
                )
            )
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
) -> SegmentFailureDetail | None:
    if order_no is None:
        failure_detail = SegmentFailureDetail(
            segment_index=segment_index,
            http_status=http_status,
            message=message,
        )
        segment_monitor.record_failed(
            pipeline_run_id=pipeline_run_id,
            snapshot_path=snapshot_path,
            segment_index=segment_index,
            segment_size=segment_size,
            http_status=failure_detail.http_status,
            message=failure_detail.message,
            submitted_at_utc=submitted_at_utc,
        )
        log_fn(f"Recorded failed segment: segment_index={segment_index} http_status={http_status}")
        return failure_detail

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
    return None


def _build_failure_summary(
    *,
    pipeline_run_id: str,
    failure_details: list[SegmentFailureDetail],
    max_segments: int = 5,
    max_chars: int = 4000,
) -> str:
    total_failures = len(failure_details)
    shown_failures = failure_details[:max_segments]
    parts = [
        "["
        f"segment={detail.segment_index}, "
        f"http_status={detail.http_status}, "
        f"message={detail.message}"
        "]"
        for detail in shown_failures
    ]
    details_text = "; ".join(parts)
    if total_failures > max_segments:
        details_text = f"{details_text}; ... +{total_failures - max_segments} more"

    summary = (
        "Budget variance submission failed "
        f"(pipeline_run_id={pipeline_run_id}, failed_segments={total_failures}): "
        f"{details_text}"
    )
    return _truncate_message(summary, max_chars)


def _truncate_message(message: str, max_chars: int) -> str:
    if len(message) <= max_chars:
        return message

    suffix = "... (truncated)"
    if max_chars <= len(suffix):
        return suffix[:max_chars]
    return f"{message[: max_chars - len(suffix)]}{suffix}"
