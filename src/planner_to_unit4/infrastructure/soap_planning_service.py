from __future__ import annotations

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
        timeout: int = 60,
    ) -> None:
        self.endpoint = endpoint
        self.username = username
        self.client = client
        self.password = password
        self.timeout = timeout
        self.http_post = http_post

    def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
        items = build_postback_items(segment)
        envelope = build_soap_envelope(
            items=items,
            username=self.username,
            client=self.client,
            password=self.password,
        )
        soap_payload = serialize_soap_envelope(envelope)

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
            return {
                "order_no": None,
                "http_status": None,
                "message": str(exc),
            }

        if response.status_code != 200:
            return {
                "order_no": None,
                "http_status": response.status_code,
                "message": response.text,
            }

        parsed = parse_object_postback_response(response.text)
        return {
            "order_no": parsed.get("order_no"),
            "http_status": response.status_code,
            "message": parsed.get("message"),
        }
