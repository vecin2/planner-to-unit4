from datetime import datetime


class FakePlanningService:
    def __init__(self, response: dict[str, str | int | None] | None = None) -> None:
        self.segments: list[list[dict]] = []
        self.response = response or {
            "order_no": "fake-order",
            "http_status": 200,
            "message": None,
        }

    def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
        self.segments.append(segment)
        return dict(self.response)


class FakeSegmentMonitor:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []
        self.failures: list[dict[str, object]] = []

    def record_submitted(
        self,
        pipeline_run_id: str,
        snapshot_path: str,
        segment_index: int,
        segment_size: int,
        order_no: str,
        http_status: int | None,
        message: str | None,
        submitted_at_utc: datetime,
    ) -> None:
        self.submissions.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "snapshot_path": snapshot_path,
                "segment_index": segment_index,
                "segment_size": segment_size,
                "status": "SUBMITTED",
                "order_no": order_no,
                "http_status": http_status,
                "message": message,
                "submitted_at_utc": submitted_at_utc,
            }
        )

    def record_failed(
        self,
        pipeline_run_id: str,
        snapshot_path: str,
        segment_index: int,
        segment_size: int,
        http_status: int | None,
        message: str | None,
        submitted_at_utc: datetime,
    ) -> None:
        self.failures.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "snapshot_path": snapshot_path,
                "segment_index": segment_index,
                "segment_size": segment_size,
                "status": "FAILED",
                "order_no": None,
                "http_status": http_status,
                "message": message,
                "submitted_at_utc": submitted_at_utc,
            }
        )
