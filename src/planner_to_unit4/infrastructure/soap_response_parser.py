from __future__ import annotations

from xml.etree import ElementTree


def parse_object_postback_response(xml_text: str) -> dict[str, str | None]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return {"order_no": None, "message": None}

    order_no = None
    message = None

    for status_item in root.iter():
        if not _tag_endswith(status_item.tag, "PostbackStatusItem"):
            continue
        name = _find_child_text(status_item, "Name")
        if name != "orderno":
            continue
        order_no = _find_child_text(status_item, "Value")
        message = _find_child_text(status_item, "Message")
        break

    return {"order_no": order_no, "message": message}


def _find_child_text(element: ElementTree.Element, local_name: str) -> str | None:
    for child in list(element):
        if _tag_endswith(child.tag, local_name):
            return child.text
    return None


def _tag_endswith(tag: str, local_name: str) -> bool:
    return tag.endswith(f"}}{local_name}") or tag.endswith(f":{local_name}") or tag == local_name
