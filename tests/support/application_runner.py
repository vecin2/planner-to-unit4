from __future__ import annotations

from planner_to_unit4.application import process_budget_variance
from planner_to_unit4.infrastructure.budget_variance_items_provider import (
    BudgetVarianceItemsProvider,
)
from tests.support.fake_budget_variance_reader import FakeBudgetVarianceReader
from tests.support.fakes import FakePlanningService


class ApplicationRunner:
    def __init__(
        self,
        rows: list[dict],
        version: str,
        batch: str,
        max_batch_size: int = 2,
    ) -> None:
        budget_variance_reader = FakeBudgetVarianceReader()
        budget_variance_reader.set_rows(rows)
        self.items_provider = BudgetVarianceItemsProvider(
            reader=budget_variance_reader,
            version=version,
            batch=batch,
        )
        self.max_batch_size = max_batch_size
        self.planning_service = FakePlanningService()

    def run_process_budget_variance(self, pipeline_run_id: str, snapshot_path: str):
        return process_budget_variance.run(
            items_provider=self.items_provider,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            max_batch_size=self.max_batch_size,
            snapshot_path=snapshot_path,
        )

    def assert_batches_sent(self, expected_batches: list[list[dict]]) -> None:
        actual_batches = self.planning_service.batches
        assert actual_batches == expected_batches
