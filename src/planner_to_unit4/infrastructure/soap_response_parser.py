from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree


@dataclass(frozen=True)
class PostbackLogItem:
    row: int | None
    column: str | None
    message: str | None


@dataclass(frozen=True)
class ParsedObjectPostbackResponse:
    order_no: str | None
    status_message: str | None
    log_items: list[PostbackLogItem]
    message: str | None


@dataclass(frozen=True)
class ParsedPostbackFault:
    fault_code: str | None
    fault_string: str | None
    log_items: list[PostbackLogItem]
    message: str | None


@dataclass(frozen=True)
class ParsedSegmentSubmissionResponse:
    order_no: str | None
    status_message: str | None
    fault_code: str | None
    fault_string: str | None
    log_items: list[PostbackLogItem]
    message: str | None


def parse_segment_submission_response(
    xml_text: str,
    *,
    http_status: int,
) -> ParsedSegmentSubmissionResponse | None:
    if http_status == 200:
        parsed = parse_object_postback_response_canonical(xml_text)
        return ParsedSegmentSubmissionResponse(
            order_no=parsed.order_no,
            status_message=parsed.status_message,
            fault_code=None,
            fault_string=None,
            log_items=parsed.log_items,
            message=parsed.message,
        )

    parsed_fault = parse_postback_fault_canonical(xml_text)
    if parsed_fault is None:
        return None
    return ParsedSegmentSubmissionResponse(
        order_no=None,
        status_message=None,
        fault_code=parsed_fault.fault_code,
        fault_string=parsed_fault.fault_string,
        log_items=parsed_fault.log_items,
        message=parsed_fault.message,
    )


def parse_object_postback_response_canonical(xml_text: str) -> ParsedObjectPostbackResponse:
    root = ElementTree.fromstring(xml_text)

    order_no = None
    status_message = None
    log_items = _collect_log_items(root)

    for status_item in root.iter():
        if not _tag_endswith(status_item.tag, "PostbackStatusItem"):
            continue
        name = _find_child_text(status_item, "Name")
        if name != "orderno":
            continue
        order_no = _find_child_text(status_item, "Value")
        status_message = _find_child_text(status_item, "Message")
        break

    log_items_message = _format_log_items(log_items)
    if status_message and log_items_message:
        message = f"{status_message}; {log_items_message}"
    else:
        message = status_message or log_items_message

    return ParsedObjectPostbackResponse(
        order_no=order_no,
        status_message=status_message,
        log_items=log_items,
        message=message,
    )


def parse_postback_fault_canonical(xml_text: str) -> ParsedPostbackFault | None:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return None

    fault_code: str | None = None
    fault_string: str | None = None
    for element in root.iter():
        if _tag_endswith(element.tag, "faultcode"):
            fault_code = _normalize_text(element.text) or fault_code
        if _tag_endswith(element.tag, "faultstring"):
            fault_string = _normalize_text(element.text) or fault_string

    log_items = _collect_log_items(root)

    if fault_string:
        message = f"{fault_code}: {fault_string}" if fault_code else fault_string
    elif fault_code:
        message = fault_code
    else:
        message = _format_log_items(log_items)

    return ParsedPostbackFault(
        fault_code=fault_code,
        fault_string=fault_string,
        log_items=log_items,
        message=message,
    )


def _collect_log_items(root: ElementTree.Element) -> list[PostbackLogItem]:
    log_items: list[PostbackLogItem] = []
    for log_item in root.iter():
        if not _tag_endswith(log_item.tag, "PostbackLogItem"):
            continue
        row = _parse_optional_int(_normalize_text(_find_child_text(log_item, "Row")))
        column = _normalize_text(_find_child_text(log_item, "Column"))
        item_message = _normalize_text(_find_child_text(log_item, "Message"))
        log_items.append(
            PostbackLogItem(
                row=row,
                column=column,
                message=item_message,
            )
        )
    return log_items


def _format_log_items(log_items: list[PostbackLogItem]) -> str | None:
    if not log_items:
        return None
    return "; ".join(_format_log_item(log_item) for log_item in log_items)


def _format_log_item(log_item: PostbackLogItem) -> str:
    row_text = str(log_item.row) if log_item.row is not None else "?"
    column_text = log_item.column or "?"
    message_text = log_item.message or "?"
    return f"Row {row_text} col {column_text}: {message_text}"


def _find_child_text(element: ElementTree.Element, local_name: str) -> str | None:
    for child in list(element):
        if _tag_endswith(child.tag, local_name):
            return child.text
    return None


def _tag_endswith(tag: str, local_name: str) -> bool:
    return tag.endswith(f"}}{local_name}") or tag.endswith(f":{local_name}") or tag == local_name


def _normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.strip()
    if not normalized:
        return None
    return normalized


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
