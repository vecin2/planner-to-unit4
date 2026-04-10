from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring


POSTBACK_FIELDS_IN_ORDER = [
    "TransactionId",
    "Client",
    "Version",
    "Batch",
    "TransactionSetup",
    "Description",
    "Account",
    "Dim2",
    "Dim3",
    "Dim4",
    "Dim6",
    "Dim7",
    "Submit",
    "Currency",
    "PeriodFrom",
    "PeriodTo",
    "CurAmount",
]


def build_postback_items(rows: list[dict]) -> list[dict]:
    items = []
    for idx, row in enumerate(rows, start=1):
        item = {
            "Client": safe_str(row.get("Client")),
            "Description": safe_str(row.get("Description")),
            "Account": safe_str(row.get("Account")),
            "Dim2": safe_str(row.get("Dim2")),
            "Dim3": safe_str(row.get("Dim3")),
            "Dim4": safe_str(row.get("Dim4")),
            "Dim6": safe_str(row.get("Dim6")),
            "Dim7": safe_str(row.get("Dim7")),
            "Currency": safe_str(row.get("Currency")),
            "PeriodFrom": safe_str(row.get("Period")),
            "PeriodTo": safe_str(row.get("Period")),
            "CurAmount": safe_str(row.get("CurAmount")),
        }
        item["TransactionId"] = -idx
        item["TransactionSetup"] = _transaction_setup(item["Client"])
        item["Version"] = safe_str(row.get("Version"))
        item["Batch"] = safe_str(row.get("Batch"))
        item["Submit"] = 0
        items.append(item)
    return items


def build_soap_envelope(
    items: list[dict],
    username: str,
    client: str,
    password: str,
    parameters_list: list[dict] | None = None,
) -> Element:
    if parameters_list is None:
        parameters_list = [{"Name": "async", "Value": "1"}]

    envelope = Element(
        "soapenv:Envelope",
        {
            "xmlns:soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
            "xmlns:plan": "http://services.agresso.com/PlanningService/PlanningV201302",
        },
    )

    SubElement(envelope, "soapenv:Header")
    body = SubElement(envelope, "soapenv:Body")
    object_postback = SubElement(body, "plan:ObjectPostBack")
    postback_items = SubElement(object_postback, "plan:postbackItems")

    for item_dict in items:
        _build_postback_item_xml(postback_items, item_dict)

    _build_parameters_xml(object_postback, parameters_list)
    _build_credentials_xml(object_postback, username, client, password)

    return envelope


def serialize_soap_envelope(envelope: Element) -> str:
    return tostring(envelope, encoding="utf-8", xml_declaration=True).decode("utf-8")


def safe_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _transaction_setup(client: str) -> str:
    if client == "BI":
        return "STD"
    return "GLBUDGET"


def _build_postback_item_xml(parent_postback_items: Element, item_dict: dict) -> Element:
    item = SubElement(parent_postback_items, "plan:PostbackItem")

    for field in POSTBACK_FIELDS_IN_ORDER:
        elem = SubElement(item, f"plan:{field}")
        elem.text = safe_str(item_dict.get(field))

    return item


def _build_parameters_xml(parent_object_postback: Element, parameters_list: list[dict]) -> Element:
    parameters = SubElement(parent_object_postback, "plan:parameters")
    for param in parameters_list:
        param_elem = SubElement(parameters, "plan:PostbackParameter")
        name_elem = SubElement(param_elem, "plan:Name")
        value_elem = SubElement(param_elem, "plan:Value")
        name_elem.text = safe_str(param.get("Name"))
        value_elem.text = safe_str(param.get("Value"))
    return parameters


def _build_credentials_xml(
    parent_object_postback: Element,
    username: str,
    client: str,
    password: str,
) -> Element:
    credentials = SubElement(parent_object_postback, "plan:credentials")
    username_elem = SubElement(credentials, "plan:Username")
    client_elem = SubElement(credentials, "plan:Client")
    password_elem = SubElement(credentials, "plan:Password")

    username_elem.text = safe_str(username)
    client_elem.text = safe_str(client)
    password_elem.text = safe_str(password)
    return credentials
