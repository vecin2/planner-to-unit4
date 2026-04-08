from dataclasses import dataclass
from planner_to_unit4.infrastructure.files.file_operations import FileOperations


@dataclass
class LandingStorage:
    file_operations: FileOperations
    source_path: str
    snapshot_root_path: str

    def source_exists(self) -> bool:
        return self.file_operations.exists(self.source_path)

    def build_snapshot_path(self, pipeline_run_id: str) -> str:
        return f"{self.snapshot_root_path}/run_id={pipeline_run_id}/Plan_Data.json"

    def move_to_snapshot_path(self, pipeline_run_id: str) -> str:
        destination = self.build_snapshot_path(pipeline_run_id)
        self.file_operations.move(self.source_path, destination)
        return destination
