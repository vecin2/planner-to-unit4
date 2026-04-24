from dataclasses import dataclass
from typing import Protocol
from typing import TypedDict


@dataclass(frozen=True)
class ResolvedPostbackError:
    row_index_1_based: int | None
    column: str | None
    message: str | None
    failed_row: dict[str, object] | None


class SegmentSubmissionResult(TypedDict, total=False):
    order_no: str | None
    http_status: int | None
    message: str | None
    request_payload: str
    status_message: str | None
    fault_code: str | None
    fault_string: str | None
    resolved_errors: list[ResolvedPostbackError]


class PlanningService(Protocol):
    def send_segment(self, segment: list[dict]) -> SegmentSubmissionResult:
        """Send a segment of budget variance rows and return response details."""
        ...
