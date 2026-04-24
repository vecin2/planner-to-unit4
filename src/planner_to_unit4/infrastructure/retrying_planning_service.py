from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from planner_to_unit4.infrastructure.planning_service import PlanningService
from planner_to_unit4.infrastructure.planning_service import SegmentSubmissionResult


@dataclass
class RetryingPlanningService(PlanningService):
    service: PlanningService
    retries: int = 0
    log_fn: Callable[[str], None] | None = None

    def send_segment(self, segment: list[dict]) -> SegmentSubmissionResult:
        max_attempts = self.retries + 1
        for attempt in range(1, max_attempts + 1):
            try:
                return self.service.send_segment(segment)
            except Exception as exc:
                if attempt == max_attempts:
                    raise
                if self.log_fn is not None:
                    self.log_fn(
                        "SOAP submission retry: "
                        f"attempt={attempt + 1}/{max_attempts} error={exc}"
                    )

        raise RuntimeError("Unexpected retry loop termination")
