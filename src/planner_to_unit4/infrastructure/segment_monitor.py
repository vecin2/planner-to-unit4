from __future__ import annotations

from datetime import datetime
from typing import Protocol


class SegmentMonitor(Protocol):
    def apply_retention(self, retention_days: int, now_utc: datetime) -> None:
        """Delete monitor rows older than the configured retention window."""
        ...

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
        """Record a segment that failed to submit."""
        ...
