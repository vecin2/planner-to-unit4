from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessBudgetVarianceResult:
    pipeline_run_id: str
    status: str
    snapshot_path: str | None = None


def run(
    budget_variance_reader,
    pipeline_run_id: str,
    planning_service,
    max_batch_size: int = 15000,
    snapshot_path: str | None = None,
) -> ProcessBudgetVarianceResult:
    rows = budget_variance_reader.read_rows()

    batches = list(_chunk_rows(rows, max_batch_size))

    for batch in batches:
        planning_service.send_batch(batch)

    return ProcessBudgetVarianceResult(
        pipeline_run_id=pipeline_run_id,
        status="COMPLETED",
        snapshot_path=snapshot_path,
    )


def _chunk_rows(rows, batch_size):
    for i in range(0, len(rows), batch_size):
        yield rows[i : i + batch_size]
