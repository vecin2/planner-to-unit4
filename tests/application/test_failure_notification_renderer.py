from planner_to_unit4.application.failure_notification_renderer import render_failure_notification
from planner_to_unit4.application.submission_failure_report import SubmissionFailureReportBuilder
from planner_to_unit4.infrastructure.soap_response_parser import PostbackLogItem


def _segment(record_start: int, record_end: int) -> list[dict]:
    return [{"record_no": record_no} for record_no in range(record_start, record_end + 1)]


def test_render_failure_notification_contains_html_summary() -> None:
    builder = SubmissionFailureReportBuilder(segments=[_segment(1, 1), _segment(2, 4)])
    builder.mark_submitted(segment_index=1, message="Submitted", http_status=200)
    builder.mark_failed(
        segment_index=2,
        http_status=400,
        message="Validation errors",
        log_items=[
            PostbackLogItem(row=2, column="dim_4", message="B102395 is not a legal BUS"),
            PostbackLogItem(row=3, column="dim_4", message="B102395 is not a legal BUS"),
        ],
    )
    report = builder.build_failure_report(pipeline_run_id="run-100")

    notification = render_failure_notification(
        report=report,
        snapshot_path="Files/FPA/archive/plan_data.json",
    )

    assert "Planner Upload Result - Failed" in notification.subject
    assert "run-100" in notification.subject
    assert "<html>" in notification.html_body
    assert "Segment Summary" in notification.html_body
    assert "B102395 is not a legal BUS" in notification.html_body
    assert "pipeline_run_id=run-100" in notification.text_body


def test_render_failure_notification_escapes_html_in_messages() -> None:
    builder = SubmissionFailureReportBuilder(segments=[_segment(1, 1)])
    builder.mark_failed(
        segment_index=1,
        http_status=400,
        message="bad <value>",
        log_items=[PostbackLogItem(row=1, column="dim_4", message='bad "tag" <x>')],
    )
    report = builder.build_failure_report(pipeline_run_id="run-101")

    notification = render_failure_notification(
        report=report,
        snapshot_path="Files/FPA/archive/plan_data.json",
    )

    assert "bad &lt;value&gt;" in notification.html_body
    assert "bad &quot;tag&quot; &lt;x&gt;" in notification.html_body
