from __future__ import annotations

from xml.etree import ElementTree


def parse_object_postback_response(xml_text: str) -> dict[str, str | None | bool]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        return {
            "order_no": None,
            "message": f"ParseError: {exc}",
            "has_log_items": False,
        }

    order_no = None
    status_message = None
    log_items = []

    for log_item in root.iter():
        if not _tag_endswith(log_item.tag, "PostbackLogItem"):
            continue
        row = _find_child_text(log_item, "Row") or "?"
        column = _find_child_text(log_item, "Column") or "?"
        item_message = _find_child_text(log_item, "Message") or "?"
        log_items.append(f"Row {row} col {column}: {item_message}")

    for status_item in root.iter():
        if not _tag_endswith(status_item.tag, "PostbackStatusItem"):
            continue
        name = _find_child_text(status_item, "Name")
        if name != "orderno":
            continue
        order_no = _find_child_text(status_item, "Value")
        status_message = _find_child_text(status_item, "Message")
        break

    has_log_items = bool(log_items)
    message = "; ".join(log_items) if has_log_items else status_message

    return {
        "order_no": order_no,
        "message": message,
        "has_log_items": has_log_items,
    }


def _find_child_text(element: ElementTree.Element, local_name: str) -> str | None:
    for child in list(element):
        if _tag_endswith(child.tag, local_name):
            return child.text
    return None


def _tag_endswith(tag: str, local_name: str) -> bool:
    return tag.endswith(f"}}{local_name}") or tag.endswith(f":{local_name}") or tag == local_name
