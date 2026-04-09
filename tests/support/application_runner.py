# tests/support/application_runner.py
from __future__ import annotations

from planner_to_unit4.application import process_budget_variance
from planner_to_unit4.infrastructure.files.file_operations import FileOperations
from planner_to_unit4.infrastructure.files.landing_storage import LandingStorage
from planner_to_unit4.infrastructure.files.local_file_operations import LocalFileOperations
from tests.support.fakes import FakePlanningService
from typing import List,Any


class ApplicationRunner:
    def __init__(
        self,
        source_path: str,
        snapshot_root_path: str,
        max_batch_size: int = 2,
    ) -> None:
        self.source_path = source_path
        self.snapshot_root_path = snapshot_root_path
        self.max_batch_size = max_batch_size
        self.file_operations = LocalFileOperations()

        self.landing_storage = LandingStorage(
            file_operations=self.file_operations,
            source_path=self.source_path,
            snapshot_root_path=self.snapshot_root_path,
        )
        self.planning_service = FakePlanningService()

    def run_process_budget_variance(self, pipeline_run_id: str):

        return process_budget_variance.run(
            landing_storage=self.landing_storage,
            pipeline_run_id=pipeline_run_id,
            planning_service=self.planning_service,
            max_batch_size=self.max_batch_size,
        )

    # --- Assertions ---

    def assert_batches_sent(self, expected_batches: List[List[Any]]):
        actual_batches = self.planning_service.batches
        assert actual_batches == expected_batches

    def assert_archive_created_for(self, pipeline_run_id: str) -> None:
        snapshot_path = self.landing_storage.build_snapshot_path(pipeline_run_id)
        assert self.file_operations.exists(snapshot_path), (
            f"Expected archive snapshot to exist at {snapshot_path}"
        )
