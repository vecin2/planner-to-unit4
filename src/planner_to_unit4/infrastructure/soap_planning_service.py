from __future__ import annotations

from typing import Callable

from planner_to_unit4.infrastructure.planning_service import (
    ParsedLogItem,
    PlanningService,
    SegmentSubmissionResult,
)
from planner_to_unit4.infrastructure.soap_envelope_builder import (
    build_postback_items,
    build_soap_envelope,
    serialize_soap_envelope,
)
from planner_to_unit4.infrastructure.soap_http_client import HttpPost
from planner_to_unit4.infrastructure.soap_response_parser import (
    PostbackLogItem,
    parse_object_postback_response_canonical,
    parse_postback_fault_canonical,
)


SOAP_ACTION = "http://services.agresso.com/PlanningService/ObjectPostBack"


class SoapPlanningService(PlanningService):
    def __init__(
        self,
        endpoint: str,
        username: str,
        client: str,
        password: str,
        http_post: HttpPost,
        log_fn: Callable[[str], None],
        timeout: int = 60,
    ) -> None:
        self.endpoint = endpoint
        self.username = username
        self.client = client
        self.password = password
        self.timeout = timeout
        self.http_post = http_post
        self.log_fn = log_fn

    def send_segment(self, segment: list[dict]) -> SegmentSubmissionResult:
        items = build_postback_items(segment)
        envelope = build_soap_envelope(
            items=items,
            username=self.username,
            client=self.client,
            password=self.password,
        )
        soap_payload = serialize_soap_envelope(envelope)
        self.log_fn(
            "SOAP request: "
            f"endpoint={self.endpoint} items={len(segment)} payload_bytes={len(soap_payload)}"
        )

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": SOAP_ACTION,
        }

        try:
            response = self.http_post(
                self.endpoint,
                data=soap_payload,
                headers=headers,
                timeout=self.timeout,
            )
        except Exception as exc:  # noqa: BLE001 - boundary IO failure
            raise SoapSubmissionError(str(exc), request_payload=soap_payload) from exc

        if response.status_code != 200:
            parsed_fault = parse_postback_fault_canonical(response.text)
            message = (
                parsed_fault.message
                if parsed_fault is not None
                else _truncate_message(response.text)
            )
            self.log_fn(f"SOAP response: http_status={response.status_code} message={message}")
            return {
                "order_no": None,
                "http_status": response.status_code,
                "message": message,
                "request_payload": soap_payload,
                "fault_code": None if parsed_fault is None else parsed_fault.fault_code,
                "fault_string": None if parsed_fault is None else parsed_fault.fault_string,
                "log_items": []
                if parsed_fault is None
                else _serialize_log_items(parsed_fault.log_items),
            }

        try:
            parsed = parse_object_postback_response_canonical(response.text)
        except Exception as exc:  # noqa: BLE001 - parser failure
            raise SoapSubmissionError(str(exc), request_payload=soap_payload) from exc
        self.log_fn(
            "SOAP response: "
            f"http_status={response.status_code} order_no={parsed.order_no} "
            f"message={parsed.message}"
        )
        return {
            "order_no": parsed.order_no,
            "http_status": response.status_code,
            "message": parsed.message,
            "request_payload": soap_payload,
            "status_message": parsed.status_message,
            "log_items": _serialize_log_items(parsed.log_items),
        }


class SoapSubmissionError(RuntimeError):
    def __init__(self, message: str, request_payload: str) -> None:
        super().__init__(message)
        self.request_payload = request_payload


def _truncate_message(message: str | None, limit: int = 4000) -> str | None:
    if message is None:
        return None
    if len(message) <= limit:
        return message
    suffix = "... (truncated)"
    if limit <= len(suffix):
        return suffix[:limit]
    return f"{message[: limit - len(suffix)]}{suffix}"


def _serialize_log_items(log_items: list[PostbackLogItem]) -> list[ParsedLogItem]:
    return [
        {
            "row": item.row,
            "column": item.column,
            "message": item.message,
        }
        for item in log_items
    ]
