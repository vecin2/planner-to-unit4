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
    planning_service,
    max_batch_size: int = 15000,
) -> ProcessBudgetVarianceResult:
    import json

    # Read rows from source file BEFORE archiving
    source_content = landing_storage.read_source()
    rows = []
    for line in source_content.strip().split('\n'):
        if line.strip():
            rows.append(json.loads(line))

    snapshot_path = _archive_landing_file(
        landing_storage=landing_storage,
        pipeline_run_id=pipeline_run_id,
    )

    batches = list(_chunk_rows(rows, max_batch_size))

    # send batches
    for batch in batches:
        planning_service.send_batch(batch)
    # load budget variance records

    # build batches

    # process batches
    # make api call
    # store batch to batch monitor table (with status depending on api call result)

    return ProcessBudgetVarianceResult(
        pipeline_run_id=pipeline_run_id,
        status="COMPLETED",
        snapshot_path=snapshot_path,
    )


def _chunk_rows(rows, batch_size):
    for i in range(0, len(rows), batch_size):
        yield rows[i : i + batch_size]


def _archive_landing_file(
    landing_storage: LandingStorage,
    pipeline_run_id: str,
) -> str | None:
    if not landing_storage.source_exists():
        return None

    return landing_storage.move_to_snapshot_path(pipeline_run_id)
