from typing import Protocol

SegmentSubmissionResult = dict[str, str | int | bool | None]


class PlanningService(Protocol):
    def send_segment(self, segment: list[dict]) -> SegmentSubmissionResult:
        """Send a segment of budget variance rows and return response details."""
        ...
