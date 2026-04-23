from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from typing import Literal
from typing import Protocol

from planner_to_unit4.application.failure_notification_renderer import render_failure_notification
from planner_to_unit4.application.submission_failure_report import (
    SubmissionFailureReport,
    SubmissionFailureReportBuilder,
)
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from planner_to_unit4.infrastructure.planning_service import PlanningService
from planner_to_unit4.infrastructure.planning_service import ResolvedPostbackError
from planner_to_unit4.infrastructure.segment_monitor import SegmentMonitor
from planner_to_unit4.infrastructure.soap_planning_service import SoapSubmissionError


RunStatus = Literal["COMPLETED", "FAILED"]
LOG_ITEMS_FAILURE_MESSAGE = "Validation errors returned in postback log items."


@dataclass(frozen=True)
class SubmissionRunOutcome:
    pipeline_run_id: str
    snapshot_path: str
    status: RunStatus
    email_html_body: str
    failed_segments: int
    skipped_segments: int
    total_segments: int
    summary_text: str
    error_type: str
    error_message: str

    def is_success(self) -> bool:
        return self.status == "COMPLETED"

    def is_failed(self) -> bool:
        return self.status == "FAILED"

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "pipeline_run_id": self.pipeline_run_id,
            "snapshot_path": self.snapshot_path,
            "email_html_body": self.email_html_body,
            "failed_segments": self.failed_segments,
            "skipped_segments": self.skipped_segments,
            "total_segments": self.total_segments,
            "summary_text": self.summary_text,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


class FailedRequestFileSystem(Protocol):
    def mkdirs(self, path: str) -> None: ...

    def put(self, path: str, text: str, overwrite: bool) -> None: ...


@dataclass
class SubmitBudgetVariance:
    items_provider: BudgetVarianceItemsProvider
    planning_service: PlanningService
    segment_monitor: SegmentMonitor
    log_fn: Callable[[str], None]
    max_segment_size: int = 15000
    segment_monitor_retention_days: int | None = None
    failed_request_fs: FailedRequestFileSystem | None = None
    clock: Callable[[], datetime] = datetime.utcnow

    def run(self, pipeline_run_id: str, snapshot_path: str) -> SubmissionRunOutcome:
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

        report_builder = SubmissionFailureReportBuilder(segments=segments)

        for segment_index, segment in enumerate(segments, start=1):
            self.log_fn(f"Submitting segment {segment_index}/{len(segments)} size={len(segment)}")
            try:
                result = self.planning_service.send_segment(segment)
            except Exception as exc:  # noqa: BLE001 - boundary IO failure
                failure_time_utc = self.clock()
                report_builder.mark_failed(
                    segment_index=segment_index,
                    http_status=None,
                    message=str(exc),
                    resolved_errors=[],
                )
                report_builder.mark_skipped_after(failed_segment_index=segment_index)
                self.segment_monitor.record_failed(
                    pipeline_run_id=pipeline_run_id,
                    snapshot_path=snapshot_path,
                    segment_index=segment_index,
                    segment_size=len(segment),
                    http_status=None,
                    message=str(exc),
                    submitted_at_utc=failure_time_utc,
                )
                request_payload = _extract_request_payload(exc)
                self._save_failed_request_payload(
                    snapshot_path=snapshot_path,
                    pipeline_run_id=pipeline_run_id,
                    segment_index=segment_index,
                    request_payload=request_payload,
                    now_utc=failure_time_utc,
                )
                self.log_fn(f"Recorded failed segment: segment_index={segment_index} error={exc}")
                return _build_failed_outcome(
                    pipeline_run_id=pipeline_run_id,
                    snapshot_path=snapshot_path,
                    report=report_builder.build_failure_report(pipeline_run_id=pipeline_run_id),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )

            order_no = _as_optional_str(result.get("order_no"))
            self.log_fn(
                "Segment response: "
                f"segment_index={segment_index} http_status={result.get('http_status')} "
                f"order_no={order_no} message={result.get('message')}"
            )
            http_status = _as_optional_int(result.get("http_status"))
            message = _as_optional_str(result.get("message"))

            if order_no is None:
                resolved_errors = _extract_resolved_errors(result.get("resolved_errors"))
                normalized_message = _normalize_failed_segment_message(
                    message=message,
                    resolved_errors=resolved_errors,
                )
                self.segment_monitor.record_failed(
                    pipeline_run_id=pipeline_run_id,
                    snapshot_path=snapshot_path,
                    segment_index=segment_index,
                    segment_size=len(segment),
                    http_status=http_status,
                    message=normalized_message,
                    submitted_at_utc=self.clock(),
                )
                self.log_fn(
                    f"Recorded failed segment: segment_index={segment_index} http_status={http_status}"
                )
                report_builder.mark_failed(
                    segment_index=segment_index,
                    http_status=http_status,
                    message=normalized_message,
                    resolved_errors=resolved_errors,
                )
                self._save_failed_request_payload(
                    snapshot_path=snapshot_path,
                    pipeline_run_id=pipeline_run_id,
                    segment_index=segment_index,
                    request_payload=result.get("request_payload"),
                    now_utc=self.clock(),
                )
                continue

            self.segment_monitor.record_submitted(
                pipeline_run_id=pipeline_run_id,
                snapshot_path=snapshot_path,
                segment_index=segment_index,
                segment_size=len(segment),
                order_no=order_no,
                http_status=http_status,
                message=message,
                submitted_at_utc=self.clock(),
            )
            self.log_fn(
                f"Recorded submitted segment: segment_index={segment_index} order_no={order_no}"
            )
            report_builder.mark_submitted(
                segment_index=segment_index,
                message=message,
                http_status=http_status,
            )

        self.log_fn(
            "Completed budget variance submission: "
            f"pipeline_run_id={pipeline_run_id} snapshot_path={snapshot_path}"
        )

        if report_builder.has_failures():
            return _build_failed_outcome(
                pipeline_run_id=pipeline_run_id,
                snapshot_path=snapshot_path,
                report=report_builder.build_failure_report(pipeline_run_id=pipeline_run_id),
                error_type="SEGMENT_FAILURE",
                error_message="One or more segments failed",
            )

        return SubmissionRunOutcome(
            pipeline_run_id=pipeline_run_id,
            snapshot_path=snapshot_path,
            status="COMPLETED",
            email_html_body="",
            failed_segments=0,
            skipped_segments=0,
            total_segments=len(segments),
            summary_text=_build_run_summary_text(
                status="COMPLETED",
                failed_segments=0,
                skipped_segments=0,
                total_segments=len(segments),
                reason=None,
            ),
            error_type="",
            error_message="",
        )

    def _save_failed_request_payload(
        self,
        *,
        snapshot_path: str,
        pipeline_run_id: str,
        segment_index: int,
        request_payload: object,
        now_utc: datetime,
    ) -> None:
        if self.failed_request_fs is None:
            return
        if not isinstance(request_payload, str) or not request_payload:
            return

        folder_path = _build_failed_requests_path(snapshot_path)
        file_name = _build_failed_request_file_name(
            pipeline_run_id=pipeline_run_id,
            segment_index=segment_index,
            now_utc=now_utc,
        )
        file_path = f"{folder_path}/{file_name}"

        try:
            self.failed_request_fs.mkdirs(folder_path)
            self.failed_request_fs.put(file_path, request_payload, True)
            self.log_fn(
                f"Saved failed SOAP request payload: segment_index={segment_index} path={file_path}"
            )
        except Exception as exc:  # noqa: BLE001 - payload save should not block submission
            self.log_fn(
                f"Failed request payload warning: segment_index={segment_index} error={exc}"
            )


def _build_failed_outcome(
    *,
    pipeline_run_id: str,
    snapshot_path: str,
    report: SubmissionFailureReport,
    error_type: str,
    error_message: str,
) -> SubmissionRunOutcome:
    notification = render_failure_notification(
        report=report,
        snapshot_path=snapshot_path,
    )
    return SubmissionRunOutcome(
        pipeline_run_id=pipeline_run_id,
        snapshot_path=snapshot_path,
        status="FAILED",
        email_html_body=notification.html_body,
        failed_segments=report.failed_segments,
        skipped_segments=report.skipped_segments,
        total_segments=report.total_segments,
        summary_text=_build_run_summary_text(
            status="FAILED",
            failed_segments=report.failed_segments,
            skipped_segments=report.skipped_segments,
            total_segments=report.total_segments,
            reason=_resolve_failure_reason(report),
        ),
        error_type=error_type,
        error_message=error_message,
    )


def _build_run_summary_text(
    *,
    status: RunStatus,
    failed_segments: int,
    skipped_segments: int,
    total_segments: int,
    reason: str | None,
) -> str:
    base = f"{status} | failed={failed_segments} skipped={skipped_segments} total={total_segments}"
    if status == "COMPLETED":
        return base
    return f"{base} | reason={reason or 'Unknown failure'}"


def _resolve_failure_reason(report: SubmissionFailureReport) -> str:
    reasons = {
        summary.message.strip()
        for summary in report.summaries
        if summary.status == "FAILED" and summary.message is not None and summary.message.strip()
    }
    if not reasons:
        return "Unknown failure"
    if len(reasons) == 1:
        return next(iter(reasons))
    return "Multiple segment failures"


def _segment_rows(rows: list, segment_size: int):
    for i in range(0, len(rows), segment_size):
        yield rows[i : i + segment_size]


def _extract_request_payload(exc: Exception) -> str | None:
    if isinstance(exc, SoapSubmissionError):
        return exc.request_payload
    request_payload = getattr(exc, "request_payload", None)
    if isinstance(request_payload, str):
        return request_payload
    return None


def _build_failed_requests_path(snapshot_path: str) -> str:
    base_path = snapshot_path.rsplit("/", 1)[0]
    return f"{base_path}/failed_requests"


def _build_failed_request_file_name(
    *,
    pipeline_run_id: str,
    segment_index: int,
    now_utc: datetime,
) -> str:
    timestamp = now_utc.strftime("%H%M%S%f")
    return f"{timestamp}_{pipeline_run_id}_segment_{segment_index}.xml"


def _extract_resolved_errors(raw_resolved_errors: object) -> list[ResolvedPostbackError]:
    if not isinstance(raw_resolved_errors, list):
        return []

    parsed: list[ResolvedPostbackError] = []
    for raw in raw_resolved_errors:
        if isinstance(raw, ResolvedPostbackError):
            parsed.append(raw)
            continue
        if not isinstance(raw, dict):
            continue
        raw_failed_row = raw.get("failed_row")
        failed_row: dict[str, object] | None
        if isinstance(raw_failed_row, dict):
            failed_row = raw_failed_row
        else:
            failed_row = None
        parsed.append(
            ResolvedPostbackError(
                row_index_1_based=_as_optional_int(raw.get("row_index_1_based")),
                column=_as_optional_str(raw.get("column")),
                message=_as_optional_str(raw.get("message")),
                failed_row=failed_row,
            )
        )
    return parsed


def _as_optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _as_optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize_failed_segment_message(
    *,
    message: str | None,
    resolved_errors: list[ResolvedPostbackError],
) -> str | None:
    if resolved_errors:
        return LOG_ITEMS_FAILURE_MESSAGE
    return message
