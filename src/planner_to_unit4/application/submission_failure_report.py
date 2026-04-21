from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Literal

from planner_to_unit4.infrastructure.soap_response_parser import PostbackLogItem


SegmentStatus = Literal["SUBMITTED", "FAILED", "SKIPPED"]


@dataclass(frozen=True)
class SegmentErrorGroup:
    column: str | None
    message: str | None
    affected_records: int
    row_samples: list[int]


@dataclass(frozen=True)
class SegmentFailureSummary:
    segment_index: int
    record_count: int
    record_no_start: int | None
    record_no_end: int | None
    status: SegmentStatus
    http_status: int | None
    message: str | None
    skipped_reason: str | None
    error_groups: list[SegmentErrorGroup]
    has_partial_errors_notice: bool


@dataclass(frozen=True)
class SubmissionFailureReport:
    pipeline_run_id: str
    total_segments: int
    failed_segments: int
    skipped_segments: int
    summaries: list[SegmentFailureSummary]


@dataclass
class SubmissionFailureReportBuilder:
    segments: list[list[dict]]
    row_sample_limit: int = 10

    def __post_init__(self) -> None:
        self._states: dict[int, SegmentFailureSummary] = {
            index: SegmentFailureSummary(
                segment_index=index,
                record_count=len(segment),
                record_no_start=_extract_record_no(segment[0]) if segment else None,
                record_no_end=_extract_record_no(segment[-1]) if segment else None,
                status="SUBMITTED",
                http_status=None,
                message=None,
                skipped_reason=None,
                error_groups=[],
                has_partial_errors_notice=False,
            )
            for index, segment in enumerate(self.segments, start=1)
        }

    def mark_submitted(
        self, *, segment_index: int, message: str | None, http_status: int | None
    ) -> None:
        state = self._states[segment_index]
        self._states[segment_index] = replace(
            state,
            status="SUBMITTED",
            http_status=http_status,
            message=message,
            skipped_reason=None,
            error_groups=[],
            has_partial_errors_notice=False,
        )

    def mark_failed(
        self,
        *,
        segment_index: int,
        http_status: int | None,
        message: str | None,
        log_items: list[PostbackLogItem],
    ) -> None:
        state = self._states[segment_index]
        error_groups, has_partial_errors_notice = _build_error_groups(
            log_items,
            row_sample_limit=self.row_sample_limit,
        )
        self._states[segment_index] = replace(
            state,
            status="FAILED",
            http_status=http_status,
            message=message,
            skipped_reason=None,
            error_groups=error_groups,
            has_partial_errors_notice=has_partial_errors_notice,
        )

    def mark_skipped_after(self, *, failed_segment_index: int) -> None:
        for segment_index in range(failed_segment_index + 1, len(self.segments) + 1):
            state = self._states[segment_index]
            self._states[segment_index] = replace(
                state,
                status="SKIPPED",
                http_status=None,
                message=None,
                skipped_reason=(
                    f"Skipped: not attempted due to fail-fast after segment {failed_segment_index}."
                ),
                error_groups=[],
                has_partial_errors_notice=False,
            )

    def has_failures(self) -> bool:
        return any(state.status == "FAILED" for state in self._states.values())

    def build_failure_report(self, *, pipeline_run_id: str) -> SubmissionFailureReport:
        summaries = [self._states[index] for index in sorted(self._states)]
        failed_segments = sum(1 for summary in summaries if summary.status == "FAILED")
        skipped_segments = sum(1 for summary in summaries if summary.status == "SKIPPED")
        return SubmissionFailureReport(
            pipeline_run_id=pipeline_run_id,
            total_segments=len(summaries),
            failed_segments=failed_segments,
            skipped_segments=skipped_segments,
            summaries=summaries,
        )


def format_failure_report(report: SubmissionFailureReport) -> str:
    lines = [
        "Budget variance submission failed "
        f"(pipeline_run_id={report.pipeline_run_id}, "
        f"failed_segments={report.failed_segments}, "
        f"skipped_segments={report.skipped_segments}, "
        f"total_segments={report.total_segments})",
        "Segment summary:",
    ]

    for summary in report.summaries:
        lines.append(
            "- "
            f"segment={summary.segment_index} "
            f"records={summary.record_count} "
            f"range={_format_range(summary.record_no_start, summary.record_no_end)} "
            f"status={_status_label(summary.status)}"
            f"{_format_http_status(summary.http_status)}"
            f"{_format_message(summary.status, summary.message, summary.skipped_reason)}"
        )
        if summary.status != "FAILED":
            continue
        for error in summary.error_groups:
            lines.append(
                "  - "
                f"column={error.column or '?'} "
                f"message={error.message or '?'} "
                f"affected_records={error.affected_records} "
                f"row_samples={_format_row_samples(error.row_samples)}"
            )
        if summary.has_partial_errors_notice:
            lines.append(
                "  - note=Source returned partial errors; "
                "only the first 100 errors were returned by the web service"
            )
    return "\n".join(lines)


def _build_error_groups(
    log_items: list[PostbackLogItem],
    *,
    row_sample_limit: int,
) -> tuple[list[SegmentErrorGroup], bool]:
    grouped: dict[tuple[str | None, str | None], list[PostbackLogItem]] = {}
    has_partial_errors_notice = False
    for log_item in log_items:
        if _is_partial_errors_notice(log_item):
            has_partial_errors_notice = True
            continue
        key = (log_item.column, log_item.message)
        grouped.setdefault(key, []).append(log_item)

    grouped_summaries: list[SegmentErrorGroup] = []
    for column, message in sorted(grouped):
        items = grouped[(column, message)]
        valid_rows = sorted({item.row for item in items if item.row is not None and item.row > 0})
        row_samples = valid_rows[:row_sample_limit]
        affected_records = len(valid_rows) if valid_rows else len(items)
        grouped_summaries.append(
            SegmentErrorGroup(
                column=column,
                message=message,
                affected_records=affected_records,
                row_samples=row_samples,
            )
        )
    return grouped_summaries, has_partial_errors_notice


def _is_partial_errors_notice(log_item: PostbackLogItem) -> bool:
    if log_item.row != 0 or log_item.message is None:
        return False
    return "first 100 errors" in log_item.message.lower()


def _extract_record_no(row: dict) -> int | None:
    record_no = row.get("record_no")
    if isinstance(record_no, int):
        return record_no
    if isinstance(record_no, str):
        try:
            return int(record_no)
        except ValueError:
            return None
    return None


def _status_label(status: SegmentStatus) -> str:
    if status == "SUBMITTED":
        return "Submitted"
    if status == "FAILED":
        return "Failed"
    return "Skipped"


def _format_range(start: int | None, end: int | None) -> str:
    start_text = "?" if start is None else str(start)
    end_text = "?" if end is None else str(end)
    return f"{start_text}-{end_text}"


def _format_http_status(http_status: int | None) -> str:
    if http_status is None:
        return ""
    return f" http_status={http_status}"


def _format_message(status: SegmentStatus, message: str | None, skipped_reason: str | None) -> str:
    if status == "SKIPPED":
        return f" message={skipped_reason}" if skipped_reason else ""
    if not message:
        return ""
    return f" message={message}"


def _format_row_samples(row_samples: list[int]) -> str:
    if not row_samples:
        return "-"
    return ", ".join(str(row) for row in row_samples)
