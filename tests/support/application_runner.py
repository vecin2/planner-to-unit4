from __future__ import annotations

from planner_to_unit4.application import process_budget_variance
from tests.support.fakes import FakePlanningService
class ApplicationRunner:
    def __init__(
        self,
        items_provider,
        max_batch_size: int = 2,
        snapshot_path: str | None = None,
    ) -> None:
        self.items_provider = items_provider
        self.max_batch_size = max_batch_size
        self.snapshot_path = snapshot_path
        self.planning_service = FakePlanningService()

    def run_process_budget_variance(self, pipeline_run_id: str):
        return process_budget_variance.run(
            items_provider=self.items_provider,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            max_batch_size=self.max_batch_size,
            snapshot_path=self.snapshot_path,
        )

    def assert_batches_sent(self, expected_batches: list[list[dict]]) -> None:
        actual_batches = self.planning_service.batches
        assert actual_batches == expected_batches
