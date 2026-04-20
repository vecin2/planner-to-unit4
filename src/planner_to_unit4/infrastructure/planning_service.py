from typing import Protocol
from typing import TypedDict


class ParsedLogItem(TypedDict):
    row: int | None
    column: str | None
    message: str | None


class SegmentSubmissionResult(TypedDict, total=False):
    order_no: str | None
    http_status: int | None
    message: str | None
    request_payload: str
    status_message: str | None
    fault_code: str | None
    fault_string: str | None
    log_items: list[ParsedLogItem]


class PlanningService(Protocol):
    def send_segment(self, segment: list[dict]) -> SegmentSubmissionResult:
        """Send a segment of budget variance rows and return response details."""
        ...
