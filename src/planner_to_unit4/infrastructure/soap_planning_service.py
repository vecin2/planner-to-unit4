from __future__ import annotations

from typing import Callable

from planner_to_unit4.infrastructure.planning_service import (
    PlanningService,
    ResolvedPostbackError,
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
    parse_segment_submission_response,
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

        try:
            parsed = parse_segment_submission_response(
                response.text,
                http_status=response.status_code,
            )
        except Exception as exc:  # noqa: BLE001 - parser failure
            raise SoapSubmissionError(str(exc), request_payload=soap_payload) from exc

        self.log_fn(
            "SOAP response: "
            f"http_status={response.status_code} order_no={parsed.order_no} "
            f"message={parsed.message}"
        )
        resolved_errors = _resolve_postback_errors(parsed.log_items, segment)
        return {
            "order_no": parsed.order_no,
            "http_status": response.status_code,
            "message": parsed.message,
            "request_payload": soap_payload,
            "status_message": parsed.status_message,
            "fault_code": parsed.fault_code,
            "fault_string": parsed.fault_string,
            "resolved_errors": resolved_errors,
        }


class SoapSubmissionError(RuntimeError):
    def __init__(self, message: str, request_payload: str) -> None:
        super().__init__(message)
        self.request_payload = request_payload


def _resolve_postback_errors(
    log_items: list[PostbackLogItem],
    segment: list[dict],
) -> list[ResolvedPostbackError]:
    resolved_errors: list[ResolvedPostbackError] = []
    for log_item in log_items:
        if _is_partial_errors_notice(log_item):
            continue
        resolved_errors.append(_resolve_postback_error(log_item, segment))
    return resolved_errors


def _resolve_postback_error(
    log_item: PostbackLogItem,
    segment: list[dict],
) -> ResolvedPostbackError:
    row_index_1_based = _normalize_row_index(log_item.row)
    failed_row = _extract_failed_row(segment, row_index_1_based)
    return ResolvedPostbackError(
        row_index_1_based=row_index_1_based,
        column=log_item.column,
        message=log_item.message,
        failed_row=failed_row,
    )


def _normalize_row_index(row: int | None) -> int | None:
    if row is None or row <= 0:
        return None
    return row


def _extract_failed_row(
    segment: list[dict],
    row_index_1_based: int | None,
) -> dict[str, object] | None:
    if row_index_1_based is None:
        return None
    if row_index_1_based > len(segment):
        return None
    failed_row = segment[row_index_1_based - 1]
    if not isinstance(failed_row, dict):
        return None
    return dict(failed_row)


def _is_partial_errors_notice(log_item: PostbackLogItem) -> bool:
    if log_item.row != 0 or log_item.message is None:
        return False
    return "first 100 errors" in log_item.message.lower()
