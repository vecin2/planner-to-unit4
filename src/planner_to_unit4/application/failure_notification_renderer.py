from __future__ import annotations

from dataclasses import dataclass
from html import escape

from planner_to_unit4.application.submission_failure_report import SegmentErrorGroup
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
    total_records = sum(summary.record_count for summary in report.summaries)
    submitted_segments = sum(1 for summary in report.summaries if summary.status == "SUBMITTED")
    overall_status = "FAILED" if report.failed_segments > 0 else "COMPLETED"
    segment_sections = "".join(
        _render_segment(summary, row_sample_limit=report.row_sample_limit)
        for summary in report.summaries
    )

    return (
        "<!doctype html>"
        "<html lang='en'><head><meta charset='utf-8' />"
        "<meta name='viewport' content='width=device-width, initial-scale=1' />"
        "<style>"
        ":root{--bg:#f5f7fb;--card:#ffffff;--line:#e4e8f0;--text:#1f2937;--muted:#5b6473;--ok-bg:#e8faf0;--ok-text:#0b6b3d;--bad-bg:#fdeaea;--bad-text:#991b1b;--skip-bg:#eef2f7;--skip-text:#344054;}"
        "*{box-sizing:border-box;}"
        "body{margin:0;padding:24px;background:radial-gradient(circle at top right,#eef6ff,var(--bg));color:var(--text);font:14px/1.5 'Segoe UI',Tahoma,sans-serif;}"
        ".wrapper{max-width:1120px;margin:0 auto;}"
        ".card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:0 8px 24px rgba(20,31,54,0.06);}"
        ".header{padding:20px 24px;border-bottom:1px solid var(--line);}"
        ".title{margin:0;font-size:22px;}"
        ".meta{margin:6px 0 0;color:var(--muted);font-size:13px;}"
        ".content{padding:20px 24px 24px;}"
        ".stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:18px;}"
        ".stat{border:1px solid var(--line);background:#f8fafe;border-radius:8px;padding:10px 12px;}"
        ".stat .label{display:block;color:var(--muted);font-size:12px;}"
        ".stat .value{display:block;margin-top:2px;font-size:18px;font-weight:600;}"
        ".segment{margin-top:12px;border:1px solid var(--line);border-radius:10px;overflow:hidden;}"
        ".segment-head{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:12px 14px;border-bottom:1px solid var(--line);background:#f9fbff;}"
        ".segment-meta{color:var(--muted);font-size:13px;}"
        ".status-badge{display:inline-block;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;}"
        ".status-submitted{background:var(--ok-bg);color:var(--ok-text);}"
        ".status-failed{background:var(--bad-bg);color:var(--bad-text);}"
        ".status-skipped{background:var(--skip-bg);color:var(--skip-text);}"
        ".segment-body{padding:12px 14px 14px;}"
        ".group{margin-top:10px;border:1px solid var(--line);border-radius:8px;overflow:hidden;}"
        ".group-head{padding:10px 12px;background:#fcfdff;border-bottom:1px solid var(--line);}"
        ".group-head .key{color:var(--bad-text);font-weight:700;}"
        ".group-head .sub{margin-left:8px;color:var(--muted);font-size:12px;}"
        ".sample-note{margin:8px 0 0;color:var(--muted);font-size:12px;}"
        ".table-wrap{overflow-x:auto;}"
        "table{width:100%;border-collapse:collapse;}"
        "th,td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top;font-size:12px;}"
        "th{background:#f2f5fb;white-space:nowrap;}"
        "@media (max-width:980px){body{padding:12px;}.header,.content{padding-left:14px;padding-right:14px;}.stats{grid-template-columns:repeat(2,minmax(0,1fr));}}"
        "</style></head><body>"
        "<div class='wrapper'><article class='card'>"
        "<header class='header'>"
        "<h1 class='title'>Planner Upload Result</h1>"
        f"<p class='meta'>Pipeline Run ID: <strong>{_escape(report.pipeline_run_id)}</strong>"
        f" | Archived File: <strong>{_escape(snapshot_path)}</strong></p>"
        "</header><section class='content'>"
        "<div class='stats'>"
        f"<div class='stat'><span class='label'>Total Records</span><span class='value'>{total_records}</span></div>"
        f"<div class='stat'><span class='label'>Segments Submitted</span><span class='value'>{submitted_segments}</span></div>"
        f"<div class='stat'><span class='label'>Segments Failed</span><span class='value'>{report.failed_segments}</span></div>"
        f"<div class='stat'><span class='label'>Status</span><span class='value'>{overall_status}</span></div>"
        "</div>"
        f"{segment_sections}"
        "</section>"
        "</article></div></body></html>"
    )


def _render_segment(summary: SegmentFailureSummary, *, row_sample_limit: int) -> str:
    http_part = (
        f"<span class='segment-meta'>HTTP: <strong>{summary.http_status}</strong></span>"
        if summary.http_status is not None
        else ""
    )
    return (
        "<section class='segment'>"
        "<div class='segment-head'>"
        f"<strong>Segment {summary.segment_index}</strong>"
        f"{_render_status_badge(summary.status)}"
        f"<span class='segment-meta'>Records: <strong>{summary.record_count}</strong></span>"
        f"<span class='segment-meta'>Range: <strong>{_escape(_format_range(summary.record_no_start, summary.record_no_end))}</strong></span>"
        f"{http_part}"
        "</div>"
        f"{_render_segment_body(summary, row_sample_limit=row_sample_limit)}"
        "</section>"
    )


def _render_segment_body(summary: SegmentFailureSummary, *, row_sample_limit: int) -> str:
    if summary.status == "SUBMITTED":
        return "<div class='segment-body'>No validation errors.</div>"
    if summary.status == "SKIPPED":
        reason = summary.skipped_reason or "Skipped"
        return f"<div class='segment-body'>{_escape(reason)}</div>"
    if summary.error_groups:
        groups_html = "".join(
            _render_error_group(group, row_sample_limit=row_sample_limit)
            for group in summary.error_groups
        )
        return f"<div class='segment-body'>{groups_html}</div>"
    message = summary.message or "Failed"
    return f"<div class='segment-body'>{_escape(message)}</div>"


def _render_error_group(group: SegmentErrorGroup, *, row_sample_limit: int) -> str:
    group_message = _escape(group.message or "?")
    row_headers = "".join(
        f"<th>{_escape(label)}</th>" for _field_name, label in _failed_row_columns()
    )
    row_cells = "".join(_render_failed_row_row(row) for row in group.failed_row_samples)
    if not row_cells:
        row_cells = _render_failed_row_row(None)
    return (
        "<section class='group'>"
        "<div class='group-head'>"
        f"<strong><span class='key'>Error:</span> {group_message}</strong>"
        f"<span class='sub'>| Rows affected: {group.affected_records}</span>"
        "</div>"
        f"<p class='sample-note'>Sample failed rows (showing up to {row_sample_limit})</p>"
        "<div class='table-wrap'><table><thead><tr>"
        f"{row_headers}"
        "</tr></thead><tbody>"
        f"{row_cells}"
        "</tbody></table></div></section>"
    )


def _render_failed_row_row(row: dict[str, object] | None) -> str:
    cells = "".join(
        f"<td>{_escape(_failed_row_value(row, field_name))}</td>"
        for field_name, _label in _failed_row_columns()
    )
    return f"<tr>{cells}</tr>"


def _failed_row_columns() -> tuple[tuple[str, str], ...]:
    return (
        ("record_no", "record_no"),
        ("Client", "Client"),
        ("Description", "Description"),
        ("Account", "Account"),
        ("Dim2", "Dim2"),
        ("Dim3", "Dim3"),
        ("Dim4", "Dim4"),
        ("Dim6", "Dim6"),
        ("Dim7", "Dim7"),
        ("Currency", "Currency"),
        ("Period", "Period"),
        ("CurAmount", "CurAmount"),
    )


def _failed_row_value(row: dict[str, object] | None, field_name: str) -> str:
    if row is None:
        if field_name == "Description":
            return "Unresolved row index from source service"
        return "?"

    value = row.get(field_name)
    if value is None:
        return "?"
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else "?"
    return str(value)


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


def _escape(value: object) -> str:
    return escape(str(value), quote=True)
