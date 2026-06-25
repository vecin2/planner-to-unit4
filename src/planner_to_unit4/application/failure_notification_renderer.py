from __future__ import annotations

from datetime import datetime
from datetime import timezone
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
    report_generated_at_utc: datetime | None = None,
) -> FailureNotification:
    subject = f"Planner Upload Result - Failed ({report.pipeline_run_id})"
    text_body = format_failure_report(report)
    html_body = render_report_html(
        report=report,
        snapshot_path=snapshot_path,
        report_generated_at_utc=report_generated_at_utc,
    )
    return FailureNotification(
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def render_report_html(
    *,
    report: SubmissionFailureReport,
    snapshot_path: str,
    report_generated_at_utc: datetime | None = None,
) -> str:
    generated_at = report_generated_at_utc or datetime.utcnow()
    return _render_failure_html(
        report=report,
        snapshot_path=snapshot_path,
        report_generated_at_utc=generated_at,
    )


def _render_failure_html(
    *,
    report: SubmissionFailureReport,
    snapshot_path: str,
    report_generated_at_utc: datetime,
) -> str:
    total_records = sum(summary.record_count for summary in report.summaries)
    submitted_segments = sum(1 for summary in report.summaries if summary.status == "SUBMITTED")
    overall_status = "FAILED" if report.failed_segments > 0 else "COMPLETED"
    report_generated_at_text = _format_utc_timestamp(report_generated_at_utc)
    segment_sections = "".join(
        _render_segment(
            summary,
            row_sample_limit=report.row_sample_limit,
            add_top_spacing=index > 0,
        )
        for index, summary in enumerate(report.summaries)
    )

    return (
        "<!doctype html>"
        "<html lang='en'><head><meta charset='utf-8' />"
        "<meta name='viewport' content='width=device-width, initial-scale=1' />"
        "<style>"
        "body{margin:0;padding:16px;background:#ffffff;color:#111111;font:14px/1.4 Arial,sans-serif;}"
        "table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #d1d5db;padding:6px;text-align:left;vertical-align:top;font-size:12px;}"
        "th{background:#f3f4f6;white-space:nowrap;}"
        "</style></head><body>"
        "<div style='max-width:1000px;margin:0 auto;border:1px solid #d1d5db;background:#ffffff;'>"
        "<div style='padding:12px 14px;border-bottom:1px solid #d1d5db;'>"
        "<h1 style='margin:0;font-size:20px;'>Planner Upload Result</h1>"
        f"<p style='margin:6px 0 0;color:#555555;font-size:13px;'>Pipeline Run ID: <strong>{_escape(report.pipeline_run_id)}</strong>"
        f" | Archived File: <strong>{_escape(snapshot_path)}</strong>"
        f" | Report generated (UTC): <strong>{_escape(report_generated_at_text)}</strong></p>"
        "</div><div style='padding:14px;'>"
        f"{_render_stats_table(total_records, submitted_segments, report.failed_segments, overall_status)}"
        "<div style='height:14px;line-height:14px;font-size:14px;'>&nbsp;</div>"
        f"{segment_sections}"
        "</div>"
        "</div></body></html>"
    )


def _render_stats_table(
    total_records: int,
    submitted_segments: int,
    failed_segments: int,
    overall_status: str,
) -> str:
    return (
        "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' border='0' style='border-collapse:collapse;margin:0;'>"
        "<tr>"
        f"{_render_stat_cell('Total Records', str(total_records), right_padding='10px')}"
        f"{_render_stat_cell('Segments Submitted', str(submitted_segments), right_padding='10px')}"
        f"{_render_stat_cell('Segments Failed', str(failed_segments), right_padding='10px')}"
        f"{_render_stat_cell('Status', overall_status, right_padding='0', value_html=_render_report_status_text(overall_status))}"
        "</tr></table>"
    )


def _render_stat_cell(
    label: str,
    value: str,
    *,
    right_padding: str,
    value_color: str | None = None,
    value_html: str | None = None,
) -> str:
    color_style = f"color:{value_color};" if value_color else ""
    value_markup = _escape(value)
    if value_html is not None:
        value_markup = value_html
    return (
        f"<td width='25%' valign='top' style='padding:0 {right_padding} 0 0;'>"
        "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' border='0' style='border:1px solid #d1d5db;border-collapse:separate;'>"
        f"<tr><td style='padding:10px 12px 0;color:#5b6473;font-size:12px;line-height:1.4;'>{_escape(label)}</td></tr>"
        f"<tr><td style='padding:2px 12px 10px;font-size:18px;line-height:1.3;font-weight:700;{color_style}'>{value_markup}</td></tr>"
        "</table></td>"
    )


def _render_report_status_text(overall_status: str) -> str:
    if overall_status == "FAILED":
        foreground = "#991b1b"
    else:
        foreground = "#0b6b3d"
    return (
        f"<span style='font-size:18px;line-height:1.3;font-weight:700;color:{foreground};'>"
        f"<font color='{foreground}'>{_escape(overall_status)}</font>"
        "</span>"
    )


def _render_segment(
    summary: SegmentFailureSummary,
    *,
    row_sample_limit: int,
    add_top_spacing: bool,
) -> str:
    spacer = ""
    if add_top_spacing:
        spacer = "<div style='height:12px;line-height:12px;font-size:12px;'>&nbsp;</div>"
    separator = "<span style='color:#777777;'> | </span>"
    header_items = [
        f"<span style='font-size:16px;line-height:1.3;font-weight:700;color:#111111;'>Segment {summary.segment_index}</span>",
        f"<span style='font-size:13px;line-height:1.4;color:#555555;'>Status: {_render_status_badge(summary.status)}</span>",
        "<span style='font-size:13px;line-height:1.4;color:#5b6473;'>"
        f"Records: <strong style='color:#1f2937;'>{summary.record_count}</strong>"
        "</span>",
        "<span style='font-size:13px;line-height:1.4;color:#5b6473;'>"
        f"Range: <strong style='color:#1f2937;'>{_escape(_format_range(summary.record_no_start, summary.record_no_end))}</strong>"
        "</span>",
    ]
    if summary.http_status is not None:
        header_items.append(
            "<span style='font-size:13px;line-height:1.4;color:#5b6473;'>"
            f"HTTP: <strong style='color:#1f2937;'>{summary.http_status}</strong>"
            "</span>"
        )
    if summary.order_no:
        header_items.append(
            "<span style='font-size:13px;line-height:1.4;color:#5b6473;'>"
            f"Order No: <strong style='color:#1f2937;'>{_escape(summary.order_no)}</strong>"
            "</span>"
        )
    return (
        f"{spacer}"
        "<div class='segment' style='border:1px solid #d1d5db;overflow:hidden;'>"
        "<div class='segment-head' style='padding:10px 12px;background:#f6f6f6;border-bottom:1px solid #d1d5db;text-align:left;'>"
        f"{separator.join(header_items)}"
        "</div>"
        f"{_render_segment_body(summary, row_sample_limit=row_sample_limit)}"
        "</div>"
    )


def _render_segment_body(summary: SegmentFailureSummary, *, row_sample_limit: int) -> str:
    if summary.status == "SUBMITTED":
        return "<div class='segment-body' style='padding:10px 12px;'>No validation errors.</div>"
    if summary.status == "SKIPPED":
        reason = summary.skipped_reason or "Skipped"
        return f"<div class='segment-body' style='padding:10px 12px;'>{_escape(reason)}</div>"
    if summary.error_groups:
        groups_html = "".join(
            _render_error_group(group, row_sample_limit=row_sample_limit)
            for group in summary.error_groups
        )
        return f"<div class='segment-body' style='padding:10px 12px;'>{groups_html}</div>"
    message = summary.message or "Failed"
    return (
        "<div class='segment-body' style='padding:10px 12px;'>"
        f"{_render_general_error_group(message)}"
        "</div>"
    )


def _render_general_error_group(message: str) -> str:
    return (
        "<div class='group' style='border:1px solid #d1d5db;overflow:hidden;'>"
        f"{_render_error_group_head(message=message, affected_records=None, include_bottom_border=False)}"
        "</div>"
    )


def _render_error_group(group: SegmentErrorGroup, *, row_sample_limit: int) -> str:
    row_headers = "".join(
        f"<th>{_escape(label)}</th>" for _field_name, label in _failed_row_columns()
    )
    row_cells = "".join(_render_failed_row_row(row) for row in group.failed_row_samples)
    if not row_cells:
        row_cells = _render_failed_row_row(None)
    return (
        "<div class='group' style='margin-top:10px;border:1px solid #d1d5db;overflow:hidden;'>"
        f"{_render_error_group_head(message=group.message or '?', affected_records=group.affected_records, include_bottom_border=True)}"
        f"<p class='sample-note' style='margin:8px 12px 0;color:#6b7280;font-size:11px;line-height:1.3;font-weight:400;'>Sample failed rows (showing up to {row_sample_limit})</p>"
        "<div class='table-wrap' style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;'><thead><tr>"
        f"{row_headers}"
        "</tr></thead><tbody>"
        f"{row_cells}"
        "</tbody></table></div></div>"
    )


def _render_error_group_head(
    *,
    message: str,
    affected_records: int | None,
    include_bottom_border: bool,
) -> str:
    border_style = "border-bottom:1px solid #d1d5db;" if include_bottom_border else ""
    affected_text = ""
    if affected_records is not None:
        affected_text = (
            f"<span class='sub' style='color:#6b7280;font-size:12px;'>&nbsp;| Rows affected: {affected_records}</span>"
        )
    return (
        f"<div class='group-head' style='padding:8px 10px;background:#f7f7f7;{border_style}'>"
        "<span class='key' style='color:#991b1b;font-weight:700;'>Error:</span> "
        f"<span style='font-weight:400;color:#111111;'>{_escape(message)}</span>"
        f"{affected_text}"
        "</div>"
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
        foreground = "#0b6b3d"
    elif status == "FAILED":
        foreground = "#991b1b"
    else:
        foreground = "#5b6473"
    return (
        f"<span style='font-weight:700;color:{foreground};'>"
        f"<font color='{foreground}'>{_escape(_status_label(status))}</font>"
        "</span>"
    )


def _escape(value: object) -> str:
    return escape(str(value), quote=True)


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        normalized = value
    else:
        normalized = value.astimezone(timezone.utc).replace(tzinfo=None)
    return normalized.replace(microsecond=0).isoformat() + "Z"
