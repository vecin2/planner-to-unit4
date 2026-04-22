from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from html import escape
from typing import Callable
from typing import Literal
from uuid import uuid4

from planner_to_unit4.infrastructure.file_system import FileSystem


def _new_unique_id() -> str:
    return uuid4().hex


RunStatus = Literal["COMPLETED", "FAILED"]


@dataclass(frozen=True)
class ArchiveFileResult:
    source_path: str
    archived_path: str
    status: RunStatus
    email_html_body: str
    error_message: str

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "source_path": self.source_path,
            "archived_path": self.archived_path,
            "email_html_body": self.email_html_body,
            "error_message": self.error_message,
        }


@dataclass
class ArchiveFile:
    fs: FileSystem
    archive_root_path: str
    log_fn: Callable[[str], None]
    archive_retention_days: int | None = None
    clock: Callable[[], datetime] = datetime.utcnow
    id_factory: Callable[[], str] = _new_unique_id

    def run(self, source_file_path: str) -> ArchiveFileResult:
        now_utc = self.clock()
        partition_path = _build_partition_path(self.archive_root_path, now_utc)
        file_name = _build_archive_file_name(source_file_path, now_utc, self.id_factory())
        archived_path = f"{partition_path}/{file_name}"

        try:
            self.fs.mkdirs(partition_path)
            self.fs.mv(source_file_path, archived_path)
            self.log_fn(f"Archived file: source={source_file_path} destination={archived_path}")
        except Exception as exc:  # noqa: BLE001 - boundary IO failure
            error_message = str(exc)
            self.log_fn(
                "Archive file failed: "
                f"source={source_file_path} destination={archived_path} error={error_message}"
            )
            return ArchiveFileResult(
                source_path=source_file_path,
                archived_path=archived_path,
                status="FAILED",
                email_html_body=_render_archive_failure_html(
                    source_file_path=source_file_path,
                    archived_path=archived_path,
                    error_message=error_message,
                ),
                error_message=error_message,
            )

        if self.archive_retention_days is not None:
            try:
                self._apply_retention(now_utc)
            except Exception as exc:  # noqa: BLE001 - retention should not block archiving
                self.log_fn(
                    "Archive retention warning: "
                    f"retention_days={self.archive_retention_days} error={exc}"
                )

        return ArchiveFileResult(
            source_path=source_file_path,
            archived_path=archived_path,
            status="COMPLETED",
            email_html_body="",
            error_message="",
        )

    def _apply_retention(self, now_utc: datetime) -> None:
        if self.archive_retention_days is None:
            return

        cutoff_date = (now_utc - timedelta(days=self.archive_retention_days)).date()
        for day_path, day_date in _iter_partition_days(self.fs, self.archive_root_path):
            if day_date < cutoff_date:
                self.fs.rm(day_path, recurse=True)
                self.log_fn(
                    "Archive retention deleted partition: "
                    f"path={day_path} cutoff_date={cutoff_date.isoformat()}"
                )


def _build_partition_path(archive_root_path: str, now_utc: datetime) -> str:
    base_path = archive_root_path.rstrip("/")
    return f"{base_path}/yyyy={now_utc:%Y}/mm={now_utc:%m}/dd={now_utc:%d}"


def _build_archive_file_name(source_file_path: str, now_utc: datetime, unique_id: str) -> str:
    source_name = source_file_path.rstrip("/").split("/")[-1]
    timestamp = now_utc.strftime("%H%M%S%f")
    return f"{timestamp}_{unique_id}_{source_name}"


def _iter_partition_days(fs: FileSystem, archive_root_path: str):
    for year_path in _list_paths(fs, archive_root_path):
        year = _extract_partition_value(year_path, "yyyy")
        if year is None:
            continue
        for month_path in _list_paths(fs, year_path):
            month = _extract_partition_value(month_path, "mm")
            if month is None:
                continue
            for day_path in _list_paths(fs, month_path):
                day = _extract_partition_value(day_path, "dd")
                if day is None:
                    continue
                try:
                    partition_date = datetime(year=year, month=month, day=day).date()
                except ValueError:
                    continue
                yield day_path.rstrip("/"), partition_date


def _list_paths(fs: FileSystem, path: str) -> list[str]:
    paths: list[str] = []
    for entry in fs.ls(path):
        if isinstance(entry, str):
            paths.append(entry)
            continue
        entry_path = getattr(entry, "path", None)
        if isinstance(entry_path, str):
            paths.append(entry_path)
    return paths


def _extract_partition_value(path: str, key: str) -> int | None:
    token = path.rstrip("/").split("/")[-1]
    if not token.startswith(f"{key}="):
        return None
    value = token.split("=", maxsplit=1)[1]
    if not value.isdigit():
        return None
    return int(value)


def _render_archive_failure_html(
    *,
    source_file_path: str,
    archived_path: str,
    error_message: str,
) -> str:
    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8' />"
        "<meta name='viewport' content='width=device-width, initial-scale=1' />"
        "<style>"
        "body{font-family:Segoe UI,Arial,sans-serif;background:#f6f8fb;color:#1f2937;padding:16px;}"
        ".card{max-width:820px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:18px 20px;}"
        "h1{margin:0 0 12px 0;font-size:20px;}"
        "p{margin:6px 0;}"
        ".error{margin-top:10px;padding:10px;border-radius:6px;background:#fbeaea;border:1px solid #f0b5b8;color:#842029;}"
        "</style></head><body>"
        "<article class='card'>"
        "<h1>Planner Archive Result - Failed</h1>"
        f"<p><strong>Source:</strong> {escape(source_file_path, quote=True)}</p>"
        f"<p><strong>Destination:</strong> {escape(archived_path, quote=True)}</p>"
        f"<div class='error'><strong>Error:</strong> {escape(error_message, quote=True)}</div>"
        "</article></body></html>"
    )
