from __future__ import annotations

from typing import Callable

from planner_to_unit4.infrastructure.planning_service import PlanningService
from planner_to_unit4.infrastructure.soap_envelope_builder import (
    build_postback_items,
    build_soap_envelope,
    serialize_soap_envelope,
)
from planner_to_unit4.infrastructure.soap_http_client import HttpPost
from planner_to_unit4.infrastructure.soap_response_parser import parse_object_postback_response


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

    def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
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
            self.log_fn(f"SOAP request failed: error={exc}")
            return {
                "order_no": None,
                "http_status": None,
                "message": str(exc),
                "has_log_items": False,
            }

        if response.status_code != 200:
            self.log_fn(
                f"SOAP response: http_status={response.status_code} message={response.text}"
            )
            return {
                "order_no": None,
                "http_status": response.status_code,
                "message": response.text,
                "has_log_items": False,
            }

        parsed = parse_object_postback_response(response.text)
        self.log_fn(
            "SOAP response: "
            f"http_status={response.status_code} order_no={parsed.get('order_no')} "
            f"message={parsed.get('message')}"
        )
        return {
            "order_no": parsed.get("order_no"),
            "http_status": response.status_code,
            "message": parsed.get("message"),
            "has_log_items": parsed.get("has_log_items"),
        }
