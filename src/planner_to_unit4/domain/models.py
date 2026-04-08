from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    pipeline_run_id: str
    file_path: str
    status: str = "REGISTERED"


@dataclass(frozen=True)
class RegisterSnapshotResult:
    status: str
    snapshot_id: str | None = None
    message: str | None = None
