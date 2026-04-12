from __future__ import annotations

from datetime import datetime
from typing import Callable

from planner_to_unit4.application import process_budget_variance
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from tests.support.fake_budget_variance_reader import FakeBudgetVarianceReader
from tests.support.fakes import FakePlanningService, FakeSegmentMonitor


class ApplicationRunner:
    @classmethod
    def build(
        cls,
        *,
        rows: list[dict],
        version: str,
        batch: str,
        max_segment_size: int = 2,
        submitted_at: datetime | None = None,
        log_fn: Callable[[str], None] | None = None,
    ) -> "ApplicationRunner":
        clock = (lambda: submitted_at) if submitted_at else None
        return cls(
            rows=rows,
            version=version,
            batch=batch,
            max_segment_size=max_segment_size,
            clock=clock,
            log_fn=log_fn,
        )

    def __init__(
        self,
        rows: list[dict],
        version: str,
        batch: str,
        max_segment_size: int = 2,
        clock: Callable[[], datetime] | None = None,
        log_fn: Callable[[str], None] | None = None,
    ) -> None:
        budget_variance_reader = FakeBudgetVarianceReader()
        budget_variance_reader.set_rows(rows)
        self.items_provider = BudgetVarianceItemsProvider(
            reader=budget_variance_reader,
            version=version,
            batch=batch,
        )
        self.max_segment_size = max_segment_size
        self.planning_service = FakePlanningService()
        self.segment_monitor = FakeSegmentMonitor()
        self.clock = clock or datetime.utcnow
        self.log_fn = log_fn or (lambda _message: None)

    def run_process_budget_variance(self, pipeline_run_id: str, snapshot_path: str):
        return process_budget_variance.run(
            items_provider=self.items_provider,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            segment_monitor=self.segment_monitor,
            log_fn=self.log_fn,
            max_segment_size=self.max_segment_size,
            snapshot_path=snapshot_path,
            clock=self.clock,
        )

    def assert_segments_sent(self, expected_segments: list[list[dict]]) -> None:
        actual_segments = self.planning_service.segments
        assert actual_segments == expected_segments

    def assert_segments_submitted(self, expected_submissions: list[dict]) -> None:
        assert self.segment_monitor.submissions == expected_submissions

    def expected_submissions(
        self,
        *,
        pipeline_run_id: str,
        snapshot_path: str,
        segment_sizes: list[int],
        submitted_at: datetime,
        order_no: str = "fake-order",
        http_status: int | None = 200,
        message: str | None = None,
    ) -> list[dict]:
        return [
            {
                "pipeline_run_id": pipeline_run_id,
                "snapshot_path": snapshot_path,
                "segment_index": index,
                "segment_size": segment_size,
                "order_no": order_no,
                "http_status": http_status,
                "message": message,
                "submitted_at_utc": submitted_at,
            }
            for index, segment_size in enumerate(segment_sizes, start=1)
        ]
