from planner_to_unit4.application.submission_failure_report import (
    SubmissionFailureReportBuilder,
    format_failure_report,
)
from planner_to_unit4.infrastructure.soap_response_parser import PostbackLogItem


def _segment(record_start: int, record_end: int) -> list[dict]:
    return [{"record_no": record_no} for record_no in range(record_start, record_end + 1)]


def test_build_failure_report_groups_errors_by_column_and_message() -> None:
    builder = SubmissionFailureReportBuilder(segments=[_segment(1, 2), _segment(3, 5)])

    builder.mark_submitted(segment_index=1, message="Submitted", http_status=200)
    builder.mark_failed(
        segment_index=2,
        http_status=400,
        message="Validation errors",
        log_items=[
            PostbackLogItem(row=3, column="dim_4", message="B102395 is not a legal BUS"),
            PostbackLogItem(row=4, column="dim_4", message="B102395 is not a legal BUS"),
            PostbackLogItem(
                row=0,
                column=None,
                message=(
                    "There are more errors, but only the first 100 errors is returned from the web service"
                ),
            ),
        ],
    )

    report = builder.build_failure_report(pipeline_run_id="run-1")

    assert report.failed_segments == 1
    assert report.skipped_segments == 0
    assert report.summaries[0].status == "SUBMITTED"
    assert report.summaries[1].status == "FAILED"
    assert report.summaries[1].record_no_start == 3
    assert report.summaries[1].record_no_end == 5
    assert report.summaries[1].has_partial_errors_notice is True
    assert report.summaries[1].error_groups[0].column == "dim_4"
    assert report.summaries[1].error_groups[0].affected_records == 2
    assert report.summaries[1].error_groups[0].row_samples == [3, 4]


def test_mark_skipped_after_marks_remaining_segments() -> None:
    builder = SubmissionFailureReportBuilder(
        segments=[_segment(1, 1), _segment(2, 2), _segment(3, 3)],
    )

    builder.mark_submitted(segment_index=1, message="Submitted", http_status=200)
    builder.mark_failed(segment_index=2, http_status=None, message="network timeout", log_items=[])
    builder.mark_skipped_after(failed_segment_index=2)

    report = builder.build_failure_report(pipeline_run_id="run-2")

    assert [summary.status for summary in report.summaries] == ["SUBMITTED", "FAILED", "SKIPPED"]
    assert report.summaries[2].skipped_reason == (
        "Skipped: not attempted due to fail-fast after segment 2."
    )


def test_row_samples_are_limited_to_ten() -> None:
    builder = SubmissionFailureReportBuilder(segments=[_segment(1, 20)], row_sample_limit=10)
    builder.mark_failed(
        segment_index=1,
        http_status=400,
        message="Validation errors",
        log_items=[
            PostbackLogItem(row=row, column="dim_4", message="B102395 is not a legal BUS")
            for row in range(1, 16)
        ],
    )

    report = builder.build_failure_report(pipeline_run_id="run-3")

    assert report.summaries[0].error_groups[0].affected_records == 15
    assert report.summaries[0].error_groups[0].row_samples == list(range(1, 11))

    formatted = format_failure_report(report)
    assert "row_samples=1, 2, 3, 4, 5, 6, 7, 8, 9, 10" in formatted
