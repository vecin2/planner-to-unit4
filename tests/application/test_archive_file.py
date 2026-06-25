from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from planner_to_unit4.application.archive_file import ArchiveFile


@dataclass
class FileEntry:
    path: str


class FakeFileSystem:
    def __init__(self, listings: dict[str, list[FileEntry]] | None = None) -> None:
        self.listings = listings or {}
        self.mkdirs_calls: list[str] = []
        self.cp_calls: list[tuple[str, str]] = []
        self.mv_calls: list[tuple[str, str]] = []
        self.rm_calls: list[tuple[str, bool]] = []
        self.ls_calls: list[str] = []
        self.ls_error: Exception | None = None
        self.mkdirs_error: Exception | None = None
        self.cp_error: Exception | None = None
        self.mv_error: Exception | None = None

    def mkdirs(self, path: str) -> None:
        self.mkdirs_calls.append(path)
        if self.mkdirs_error is not None:
            raise self.mkdirs_error

    def cp(self, source_path: str, destination_path: str) -> None:
        self.cp_calls.append((source_path, destination_path))
        if self.cp_error is not None:
            raise self.cp_error

    def mv(self, source_path: str, destination_path: str) -> None:
        self.mv_calls.append((source_path, destination_path))
        if self.mv_error is not None:
            raise self.mv_error

    def ls(self, path: str) -> list[object]:
        self.ls_calls.append(path)
        if self.ls_error is not None:
            raise self.ls_error
        return self.listings.get(path, [])

    def rm(self, path: str, recurse: bool = False) -> None:
        self.rm_calls.append((path, recurse))


def test_archive_file_copies_to_partitioned_unique_path_by_default() -> None:
    fs = FakeFileSystem()
    log_messages: list[str] = []
    now_utc = datetime(2026, 4, 20, 12, 34, 56, 123456)
    archiver = ArchiveFile(
        fs=fs,
        archive_root_path="Files/FPA_Ingestion_Test/archive",
        archive_retention_days=None,
        log_fn=log_messages.append,
        clock=lambda: now_utc,
        id_factory=lambda: "abc123",
    )

    result = archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")

    expected_partition = "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20"
    expected_name = "123456123456_abc123_Plan_Data.json"
    expected_archived_path = f"{expected_partition}/{expected_name}"

    assert fs.mkdirs_calls == [expected_partition]
    assert fs.cp_calls == [
        (
            "Files/FPA_Ingestion_Test/landing/Plan_Data.json",
            expected_archived_path,
        )
    ]
    assert fs.mv_calls == []
    assert result.archived_path == expected_archived_path
    assert result.source_path == "Files/FPA_Ingestion_Test/landing/Plan_Data.json"
    assert result.status == "COMPLETED"
    assert result.is_success() is True
    assert result.is_failed() is False
    assert result.email_html_body == ""
    assert result.error_message == ""
    payload = result.to_payload()
    assert payload["archived_path_relative"] == (
        "FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/123456123456_abc123_Plan_Data.json"
    )
    assert any("Archived file" in message for message in log_messages)


def test_archive_file_moves_to_partitioned_unique_path_when_mode_is_move() -> None:
    fs = FakeFileSystem()
    now_utc = datetime(2026, 4, 20, 12, 34, 56, 123456)
    archiver = ArchiveFile(
        fs=fs,
        archive_root_path="Files/FPA_Ingestion_Test/archive",
        archive_retention_days=None,
        archive_write_mode="move",
        log_fn=lambda _message: None,
        clock=lambda: now_utc,
        id_factory=lambda: "abc123",
    )

    archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")

    expected_partition = "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20"
    expected_name = "123456123456_abc123_Plan_Data.json"
    expected_archived_path = f"{expected_partition}/{expected_name}"
    assert fs.cp_calls == []
    assert fs.mv_calls == [
        (
            "Files/FPA_Ingestion_Test/landing/Plan_Data.json",
            expected_archived_path,
        )
    ]


def test_archive_file_applies_retention() -> None:
    archive_root = "Files/FPA_Ingestion_Test/archive"
    listings = {
        archive_root: [
            FileEntry(f"{archive_root}/yyyy=2026"),
            FileEntry(f"{archive_root}/yyyy=2025"),
        ],
        f"{archive_root}/yyyy=2026": [
            FileEntry(f"{archive_root}/yyyy=2026/mm=04"),
        ],
        f"{archive_root}/yyyy=2026/mm=04": [
            FileEntry(f"{archive_root}/yyyy=2026/mm=04/dd=01"),
            FileEntry(f"{archive_root}/yyyy=2026/mm=04/dd=20"),
        ],
        f"{archive_root}/yyyy=2025": [
            FileEntry(f"{archive_root}/yyyy=2025/mm=12"),
        ],
        f"{archive_root}/yyyy=2025/mm=12": [
            FileEntry(f"{archive_root}/yyyy=2025/mm=12/dd=31"),
        ],
    }
    fs = FakeFileSystem(listings=listings)
    now_utc = datetime(2026, 4, 20, 12, 0, 0)
    archiver = ArchiveFile(
        fs=fs,
        archive_root_path=archive_root,
        archive_retention_days=10,
        log_fn=lambda _message: None,
        clock=lambda: now_utc,
        id_factory=lambda: "abc123",
    )

    archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")

    assert (f"{archive_root}/yyyy=2026/mm=04/dd=01", True) in fs.rm_calls
    assert (f"{archive_root}/yyyy=2025/mm=12/dd=31", True) in fs.rm_calls
    assert (f"{archive_root}/yyyy=2026/mm=04/dd=20", True) not in fs.rm_calls


def test_archive_file_logs_warning_and_continues_when_retention_fails() -> None:
    fs = FakeFileSystem()
    fs.ls_error = RuntimeError("ls failure")
    messages: list[str] = []
    archiver = ArchiveFile(
        fs=fs,
        archive_root_path="Files/FPA_Ingestion_Test/archive",
        archive_retention_days=10,
        log_fn=messages.append,
        clock=lambda: datetime(2026, 4, 20, 12, 0, 0),
        id_factory=lambda: "abc123",
    )

    result = archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")

    assert result.status == "COMPLETED"
    assert result.is_success() is True
    assert result.is_failed() is False
    assert len(fs.cp_calls) == 1
    assert any("Archive retention warning" in message for message in messages)


def test_archive_file_returns_failed_outcome_with_email_html_when_copy_fails() -> None:
    fs = FakeFileSystem()
    fs.cp_error = RuntimeError("copy failure")
    messages: list[str] = []
    archiver = ArchiveFile(
        fs=fs,
        archive_root_path="Files/FPA_Ingestion_Test/archive",
        archive_retention_days=10,
        log_fn=messages.append,
        clock=lambda: datetime(2026, 4, 20, 12, 0, 0),
        id_factory=lambda: "abc123",
    )

    result = archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")

    assert result.status == "FAILED"
    assert result.is_success() is False
    assert result.is_failed() is True
    assert result.error_message == "copy failure"
    assert "copy failure" in result.email_html_body
    payload = result.to_payload()
    assert payload["archived_path_relative"] == (
        "FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/120000000000_abc123_Plan_Data.json"
    )
    assert any("Archive file failed" in message for message in messages)


def test_archive_file_payload_has_stable_keys_for_success_and_failure() -> None:
    success_archiver = ArchiveFile(
        fs=FakeFileSystem(),
        archive_root_path="Files/FPA_Ingestion_Test/archive",
        archive_retention_days=None,
        log_fn=lambda _message: None,
        clock=lambda: datetime(2026, 4, 20, 12, 0, 0),
        id_factory=lambda: "abc123",
    )
    success_result = success_archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")

    failing_fs = FakeFileSystem()
    failing_fs.cp_error = RuntimeError("cp down")
    failing_archiver = ArchiveFile(
        fs=failing_fs,
        archive_root_path="Files/FPA_Ingestion_Test/archive",
        archive_retention_days=None,
        log_fn=lambda _message: None,
        clock=lambda: datetime(2026, 4, 20, 12, 0, 0),
        id_factory=lambda: "abc123",
    )
    failure_result = failing_archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")

    success_payload = success_result.to_payload()
    failure_payload = failure_result.to_payload()

    assert set(success_payload) == set(failure_payload)
    assert success_payload["status"] == "COMPLETED"
    assert failure_payload["status"] == "FAILED"
    assert success_payload["archived_path_relative"].startswith("FPA_Ingestion_Test/archive/")
    assert failure_payload["archived_path_relative"].startswith("FPA_Ingestion_Test/archive/")
