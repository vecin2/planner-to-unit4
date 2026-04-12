from typing import Protocol

SegmentSubmissionResult = dict[str, str | int | None]


class PlanningService(Protocol):
    def send_segment(self, segment: list[dict]) -> SegmentSubmissionResult:
        """Send a segment of budget variance rows to the planning service."""
        ...
