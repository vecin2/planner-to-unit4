from __future__ import annotations

from datetime import datetime
from typing import Protocol


class SegmentMonitor(Protocol):
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
        """Record a successfully submitted segment."""
        ...
