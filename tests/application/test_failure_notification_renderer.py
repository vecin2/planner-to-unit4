from datetime import datetime

from planner_to_unit4.application.failure_notification_renderer import render_failure_notification
from planner_to_unit4.application.submission_failure_report import SubmissionFailureReportBuilder
from planner_to_unit4.infrastructure.planning_service import ResolvedPostbackError


def _segment(record_start: int, record_end: int) -> list[dict]:
    return [{"record_no": record_no} for record_no in range(record_start, record_end + 1)]


def test_render_failure_notification_contains_html_summary() -> None:
    builder = SubmissionFailureReportBuilder(
        segments=[_segment(1, 1), _segment(2, 4), _segment(5, 5)],
        row_sample_limit=7,
    )
    builder.mark_submitted(segment_index=1, order_no="51", message="Submitted", http_status=200)
    builder.mark_failed(
        segment_index=2,
        http_status=400,
        message="Validation errors",
        resolved_errors=[
            ResolvedPostbackError(
                row_index_1_based=1,
                column="dim_4",
                message="B102395 is not a legal BUS",
                failed_row={"record_no": 2},
            ),
            ResolvedPostbackError(
                row_index_1_based=2,
                column="dim_4",
                message="B102395 is not a legal BUS",
                failed_row={"record_no": 3},
            ),
        ],
    )
    builder.mark_skipped_after(failed_segment_index=2)
    report = builder.build_failure_report(pipeline_run_id="run-100")

    notification = render_failure_notification(
        report=report,
        snapshot_path="Files/FPA/archive/plan_data.json",
        report_generated_at_utc=datetime(2026, 4, 24, 19, 5, 1),
    )

    assert "Planner Upload Result - Failed" in notification.subject
    assert "run-100" in notification.subject
    assert "<html lang='en'>" in notification.html_body
    assert "Planner Upload Result" in notification.html_body
    assert "Archived File:" in notification.html_body
    assert "Files/FPA/archive/plan_data.json" in notification.html_body
    assert "Report generated (UTC):" in notification.html_body
    assert "2026-04-24T19:05:01Z" in notification.html_body
    assert "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' border='0' style='border-collapse:collapse;margin:0;'>" in notification.html_body
    assert "Total Records</td></tr><tr><td style='padding:2px 12px 10px;font-size:18px;line-height:1.3;font-weight:700;'" in notification.html_body
    assert "font-size:16px;line-height:1.3;font-weight:700;color:#111111;'>Segment 1</span>" in notification.html_body
    assert "<span style='color:#777777;'> | </span>" in notification.html_body
    assert "B102395 is not a legal BUS" in notification.html_body
    assert "&nbsp;| Rows affected: 2" in notification.html_body
    assert "Error:" in notification.html_body
    assert "<strong><span class='key'>Error:</span>" not in notification.html_body
    assert "Sample failed rows (showing up to 7)" in notification.html_body
    assert "color:#6b7280;font-size:11px;line-height:1.3;font-weight:400;" in notification.html_body
    assert "record_no" in notification.html_body
    assert "status-badge status-submitted" not in notification.html_body
    assert "status-badge status-failed" not in notification.html_body
    assert "status-badge status-skipped" not in notification.html_body
    assert "report-status-badge" not in notification.html_body
    assert "<font color='#991b1b'>FAILED</font>" in notification.html_body
    assert "Status: <span style='font-weight:700;color:#0b6b3d;'><font color='#0b6b3d'>Submitted</font></span>" in notification.html_body
    assert "Order No: <strong style='color:#1f2937;'>51</strong>" in notification.html_body
    assert "Status: <span style='font-weight:700;color:#991b1b;'><font color='#991b1b'>Failed</font></span>" in notification.html_body
    assert "Status: <span style='font-weight:700;color:#5b6473;'><font color='#5b6473'>Skipped</font></span>" in notification.html_body
    assert "height:12px;line-height:12px;" in notification.html_body
    assert "height:14px;line-height:14px;" in notification.html_body
    assert "pipeline_run_id=run-100" in notification.text_body


def test_render_failure_notification_escapes_html_in_messages() -> None:
    builder = SubmissionFailureReportBuilder(segments=[_segment(1, 1)])
    builder.mark_failed(
        segment_index=1,
        http_status=400,
        message="bad <value>",
        resolved_errors=[
            ResolvedPostbackError(
                row_index_1_based=1,
                column="dim_4",
                message='bad "tag" <x>',
                failed_row={"record_no": 1},
            )
        ],
    )
    report = builder.build_failure_report(pipeline_run_id="run-101")

    notification = render_failure_notification(
        report=report,
        snapshot_path="Files/FPA/archive/plan_data.json",
    )

    assert "bad &quot;tag&quot; &lt;x&gt;" in notification.html_body
    assert 'bad "tag" <x>' not in notification.html_body


def test_render_failure_notification_formats_general_errors_like_group_errors() -> None:
    builder = SubmissionFailureReportBuilder(segments=[_segment(1, 2)])
    builder.mark_failed(
        segment_index=1,
        http_status=500,
        message="General submission failure",
        resolved_errors=[],
    )
    report = builder.build_failure_report(pipeline_run_id="run-102")

    notification = render_failure_notification(
        report=report,
        snapshot_path="Files/FPA/archive/plan_data.json",
    )

    assert "General submission failure" in notification.html_body
    assert "<span class='key' style='color:#991b1b;font-weight:700;'>Error:</span>" in notification.html_body
    assert "| Rows affected:" not in notification.html_body
