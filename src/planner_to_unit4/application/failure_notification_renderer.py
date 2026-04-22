from __future__ import annotations

from dataclasses import dataclass
from html import escape

from planner_to_unit4.application.submission_failure_report import SegmentFailureSummary
from planner_to_unit4.application.submission_failure_report import SubmissionFailureReport
from planner_to_unit4.application.submission_failure_report import format_failure_report


@dataclass(frozen=True)
class FailureNotification:
    subject: str
    html_body: str
    text_body: str


def render_failure_notification(
    *,
    report: SubmissionFailureReport,
    snapshot_path: str,
) -> FailureNotification:
    subject = f"Planner Upload Result - Failed ({report.pipeline_run_id})"
    text_body = format_failure_report(report)
    html_body = _render_failure_html(report=report, snapshot_path=snapshot_path)
    return FailureNotification(
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def _render_failure_html(*, report: SubmissionFailureReport, snapshot_path: str) -> str:
    rows: list[str] = []
    for summary in report.summaries:
        rows.append(
            "<tr>"
            f"<td>{summary.segment_index}</td>"
            f"<td>{summary.record_count}</td>"
            f"<td>{_escape(_format_range(summary.record_no_start, summary.record_no_end))}</td>"
            f"<td>{_render_status_badge(summary.status)}</td>"
            f"<td>{_render_error_summary_cell(summary)}</td>"
            "</tr>"
        )

    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8' />"
        "<meta name='viewport' content='width=device-width, initial-scale=1' />"
        "<style>"
        "body{font-family:Segoe UI,Arial,sans-serif;background:#f6f8fb;color:#1f2937;padding:16px;}"
        ".card{max-width:980px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:10px;}"
        ".head{padding:18px 20px;border-bottom:1px solid #e5e7eb;}"
        ".head h1{margin:0;font-size:20px;}"
        ".meta{margin-top:6px;color:#4b5563;font-size:13px;}"
        ".content{padding:18px 20px;}"
        ".stats td{border:1px solid #e5e7eb;background:#f9fafb;padding:10px;font-size:13px;}"
        "table{width:100%;border-collapse:collapse;}"
        "th,td{border:1px solid #e5e7eb;padding:8px;vertical-align:top;font-size:13px;text-align:left;}"
        "th{background:#f3f4f6;}"
        ".inner th,.inner td{font-size:12px;padding:6px;}"
        ".status-badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;}"
        ".status-submitted{background:#e8f7ee;color:#0f5132;border:1px solid #b7e1c2;}"
        ".status-failed{background:#fbeaea;color:#842029;border:1px solid #f0b5b8;}"
        ".status-skipped{background:#eef2f7;color:#344054;border:1px solid #d0d7e2;}"
        "</style></head><body>"
        "<article class='card'>"
        "<header class='head'>"
        "<h1>Planner Upload Result - Failed</h1>"
        f"<div class='meta'>Pipeline Run ID: <strong>{_escape(report.pipeline_run_id)}</strong>"
        f" | Snapshot: <strong>{_escape(snapshot_path)}</strong></div>"
        "</header>"
        "<section class='content'>"
        "<table class='stats'><tr>"
        f"<td><strong>Total Segments</strong><br>{report.total_segments}</td>"
        f"<td><strong>Failed Segments</strong><br>{report.failed_segments}</td>"
        f"<td><strong>Skipped Segments</strong><br>{report.skipped_segments}</td>"
        "</tr></table>"
        "<h2>Segment Summary</h2>"
        "<table><thead><tr>"
        "<th>Segment</th><th>Record Count</th><th>Range (record_no)</th><th>Status</th><th>Details</th>"
        "</tr></thead><tbody>"
        f"{''.join(rows)}"
        "</tbody></table>"
        "</section></article></body></html>"
    )


def _render_error_summary_cell(summary: SegmentFailureSummary) -> str:
    if summary.status == "SUBMITTED":
        return "Submitted"
    if summary.status == "SKIPPED":
        return _escape(summary.skipped_reason or "Skipped")

    details: list[str] = []
    if summary.message:
        details.append(f"<div><strong>Message:</strong> {_escape(summary.message)}</div>")
    if summary.http_status is not None:
        details.append(f"<div><strong>HTTP:</strong> {summary.http_status}</div>")
    if summary.error_groups:
        group_rows = [
            "<tr>"
            f"<td>{_escape(group.column or '?')}</td>"
            f"<td>{_escape(group.message or '?')}</td>"
            f"<td>{group.affected_records}</td>"
            f"<td>{_escape(_format_record_no_samples(group.record_no_samples))}</td>"
            "</tr>"
            for group in summary.error_groups
        ]
        details.append(
            "<table class='inner'><thead><tr>"
            "<th>Column</th><th>Message</th><th>Records Affected</th><th>Record No Samples</th>"
            "</tr></thead><tbody>"
            f"{''.join(group_rows)}"
            "</tbody></table>"
        )
    return "".join(details) if details else "Failed"


def _format_range(start: int | None, end: int | None) -> str:
    start_text = "?" if start is None else str(start)
    end_text = "?" if end is None else str(end)
    return f"{start_text}-{end_text}"


def _status_label(status: str) -> str:
    if status == "SUBMITTED":
        return "Submitted"
    if status == "FAILED":
        return "Failed"
    return "Skipped"


def _render_status_badge(status: str) -> str:
    if status == "SUBMITTED":
        css_class = "status-submitted"
    elif status == "FAILED":
        css_class = "status-failed"
    else:
        css_class = "status-skipped"
    return f"<span class='status-badge {css_class}'>{_escape(_status_label(status))}</span>"


def _format_record_no_samples(record_no_samples: list[str]) -> str:
    if not record_no_samples:
        return "-"
    return ", ".join(record_no_samples)


def _escape(value: object) -> str:
    return escape(str(value), quote=True)
