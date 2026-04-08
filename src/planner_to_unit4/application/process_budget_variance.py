from __future__ import annotations

from dataclasses import dataclass

from planner_to_unit4.infrastructure.files.landing_storage import LandingStorage


@dataclass(frozen=True)
class ProcessBudgetVarianceResult:
    pipeline_run_id: str
    status: str
    snapshot_path: str | None = None


def run(
    landing_storage: LandingStorage,
    pipeline_run_id: str,
) -> ProcessBudgetVarianceResult:
    snapshot_path = _archive_landing_file(
        landing_storage=landing_storage,
        pipeline_run_id=pipeline_run_id,
    )

    return ProcessBudgetVarianceResult(
        pipeline_run_id=pipeline_run_id,
        status="COMPLETED",
        snapshot_path=snapshot_path,
    )


def _archive_landing_file(
    landing_storage: LandingStorage,
    pipeline_run_id: str,
) -> str | None:
    if not landing_storage.source_exists():
        return None

    return landing_storage.move_to_snapshot_path(pipeline_run_id)
