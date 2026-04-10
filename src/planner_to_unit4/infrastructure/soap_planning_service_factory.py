from __future__ import annotations

import requests

from planner_to_unit4.infrastructure.soap_planning_service import SoapPlanningService


def build_soap_planning_service(
    endpoint: str,
    username: str,
    client: str,
    password: str,
    timeout: int = 60,
) -> SoapPlanningService:
    return SoapPlanningService(
        endpoint=endpoint,
        username=username,
        client=client,
        password=password,
        http_post=requests.post,
        timeout=timeout,
    )
