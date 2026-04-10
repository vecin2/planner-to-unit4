from __future__ import annotations

from planner_to_unit4.infrastructure.soap_envelope_builder import (
    build_postback_items,
    build_soap_envelope,
    serialize_soap_envelope,
)
from planner_to_unit4.infrastructure.soap_http_client import HttpPost
from planner_to_unit4.infrastructure.soap_response_parser import parse_object_postback_response


class SoapPlanningService:
    def __init__(
        self,
        endpoint: str,
        soap_action: str,
        username: str,
        client: str,
        password: str,
        version: str,
        batch: str,
        timeout: int = 60,
        http_post: HttpPost | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.soap_action = soap_action
        self.username = username
        self.client = client
        self.password = password
        self.version = version
        self.batch = batch
        self.timeout = timeout
        self.http_post = http_post

    def send_batch(self, batch: list[dict]) -> dict[str, str | int | None]:
        if self.http_post is None:
            import requests

            http_post = requests.post
        else:
            http_post = self.http_post

        items = build_postback_items(batch, version=self.version, batch=self.batch)
        envelope = build_soap_envelope(
            items=items,
            username=self.username,
            client=self.client,
            password=self.password,
        )
        soap_payload = serialize_soap_envelope(envelope)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": self.soap_action,
        }

        try:
            response = http_post(
                self.endpoint,
                data=soap_payload,
                headers=headers,
                timeout=self.timeout,
            )
        except Exception as exc:  # noqa: BLE001 - boundary IO failure
            return {
                "status": "FAILED",
                "order_no": None,
                "http_status": None,
                "message": None,
                "error_message": str(exc),
            }

        if response.status_code != 200:
            return {
                "status": "FAILED",
                "order_no": None,
                "http_status": response.status_code,
                "message": None,
                "error_message": response.text,
            }

        parsed = parse_object_postback_response(response.text)
        return {
            "status": "SUBMITTED",
            "order_no": parsed.get("order_no"),
            "http_status": response.status_code,
            "message": parsed.get("message"),
            "error_message": None,
        }
