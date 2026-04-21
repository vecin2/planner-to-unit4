from datetime import datetime

import pytest

from planner_to_unit4.infrastructure.soap_planning_service import SoapSubmissionError
from planner_to_unit4.infrastructure.soap_response_parser import PostbackLogItem
from tests.support.application_runner import ApplicationRunner
from tests.support.fakes import FakePlanningService, FakeSegmentMonitor


def make_row(
    record_no=1,
    client="BI",
    description="Test",
    account="1000",
    dim2="A1",
    dim3="X",
    dim4="B1",
    dim6="C1",
    dim7="ROM",
    currency="USD",
    period="202601",
    amount=1.0,
):
    return {
        "record_no": record_no,
        "Client": client,
        "Description": description,
        "Account": account,
        "Dim2": dim2,
        "Dim3": dim3,
        "Dim4": dim4,
        "Dim6": dim6,
        "Dim7": dim7,
        "Currency": currency,
        "Period": period,
        "CurAmount": amount,
    }


def with_version_and_batch(row: dict, version: str, batch: str) -> dict:
    enriched = dict(row)
    enriched["Version"] = version
    enriched["Batch"] = batch
    return enriched


def test_process_budget_variance_submits_one_segment_for_outbound_rows() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)
    row2 = make_row(record_no=2, description="Row2", amount=20)

    rows = [row1, row2]

    run_id = "fabric-run-123"
    max_segment_size = 3
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-123"
    submitted_at = datetime(2026, 4, 12, 12, 0, 0)
    expected_segments = [
        [
            with_version_and_batch(row1, version, batch),
            with_version_and_batch(row2, version, batch),
        ]
    ]
    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=max_segment_size,
        submitted_at=submitted_at,
    )
    expected_submissions = runner.expected_submissions(
        pipeline_run_id=run_id,
        snapshot_path=snapshot_path,
        segment_sizes=[2],
        submitted_at=submitted_at,
    )

    runner.run_process_budget_variance(run_id, snapshot_path)
    runner.assert_segments_sent(expected_segments)
    runner.assert_segments_submitted(expected_submissions)


def test_process_budget_variance_submits_multiple_segments_when_segment_size_is_small() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)
    row2 = make_row(record_no=2, description="Row2", amount=20)
    row3 = make_row(record_no=3, description="Row3", amount=30)

    rows = [row1, row2, row3]

    run_id = "fabric-run-456"
    max_segment_size = 2
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-456"
    submitted_at = datetime(2026, 4, 12, 12, 30, 0)
    expected_segments = [
        [
            with_version_and_batch(row1, version, batch),
            with_version_and_batch(row2, version, batch),
        ],
        [with_version_and_batch(row3, version, batch)],
    ]
    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=max_segment_size,
        submitted_at=submitted_at,
    )
    expected_submissions = runner.expected_submissions(
        pipeline_run_id=run_id,
        snapshot_path=snapshot_path,
        segment_sizes=[2, 1],
        submitted_at=submitted_at,
    )

    runner.run_process_budget_variance(run_id, snapshot_path)
    runner.assert_segments_sent(expected_segments)
    runner.assert_segments_submitted(expected_submissions)


def test_process_budget_variance_records_failed_segment_when_log_items_present() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    rows = [row1]

    run_id = "fabric-run-789"
    max_segment_size = 2
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-789"
    submitted_at = datetime(2026, 4, 12, 13, 45, 0)
    failure_message = "Row 2 col dim_3: B102397 is not a legal RESNO"
    planning_service = FakePlanningService(
        response={
            "order_no": None,
            "http_status": 200,
            "message": failure_message,
            "log_items": [
                PostbackLogItem(
                    row=2,
                    column="dim_3",
                    message="B102397 is not a legal RESNO",
                )
            ],
        }
    )

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=max_segment_size,
        submitted_at=submitted_at,
        planning_service=planning_service,
    )
    expected_failures = runner.expected_failures(
        pipeline_run_id=run_id,
        snapshot_path=snapshot_path,
        segment_sizes=[1],
        submitted_at=submitted_at,
        http_status=200,
        message=failure_message,
    )

    with pytest.raises(RuntimeError) as excinfo:
        runner.run_process_budget_variance(run_id, snapshot_path)

    summary = str(excinfo.value)
    assert "pipeline_run_id=fabric-run-789" in summary
    assert "failed_segments=1" in summary
    assert "segment=1 records=1 range=1-1 status=Failed http_status=200" in summary
    assert "column=dim_3 message=B102397 is not a legal RESNO affected_records=1" in summary

    runner.assert_segments_failed(expected_failures)


def test_process_budget_variance_records_failed_segment_for_non_200() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    rows = [row1]

    run_id = "fabric-run-987"
    max_segment_size = 2
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-987"
    submitted_at = datetime(2026, 4, 12, 14, 0, 0)
    failure_message = "Something went wrong."
    planning_service = FakePlanningService(
        response={
            "order_no": None,
            "http_status": 500,
            "message": failure_message,
        }
    )

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=max_segment_size,
        submitted_at=submitted_at,
        planning_service=planning_service,
    )
    expected_failures = runner.expected_failures(
        pipeline_run_id=run_id,
        snapshot_path=snapshot_path,
        segment_sizes=[1],
        submitted_at=submitted_at,
        http_status=500,
        message=failure_message,
    )

    with pytest.raises(RuntimeError) as excinfo:
        runner.run_process_budget_variance(run_id, snapshot_path)

    summary = str(excinfo.value)
    assert "pipeline_run_id=fabric-run-987" in summary
    assert "failed_segments=1" in summary
    assert "segment=1 records=1 range=1-1 status=Failed http_status=500" in summary
    assert "message=Something went wrong." in summary

    runner.assert_segments_failed(expected_failures)


def test_process_budget_variance_records_failed_segment_on_exception() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    rows = [row1]

    run_id = "fabric-run-654"
    max_segment_size = 2
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-654"
    submitted_at = datetime(2026, 4, 12, 14, 30, 0)

    class RaisingPlanningService:
        def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
            raise SoapSubmissionError(
                "network timeout",
                request_payload="<request>payload</request>",
            )

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=max_segment_size,
        submitted_at=submitted_at,
        planning_service=RaisingPlanningService(),
    )
    expected_failures = runner.expected_failures(
        pipeline_run_id=run_id,
        snapshot_path=snapshot_path,
        segment_sizes=[1],
        submitted_at=submitted_at,
        http_status=None,
        message="network timeout",
    )

    with pytest.raises(RuntimeError) as excinfo:
        runner.run_process_budget_variance(run_id, snapshot_path)

    assert isinstance(excinfo.value.__cause__, SoapSubmissionError)
    assert str(excinfo.value.__cause__) == "network timeout"
    summary = str(excinfo.value)
    assert "pipeline_run_id=fabric-run-654" in summary
    assert "failed_segments=1" in summary
    assert "segment=1 records=1 range=1-1 status=Failed message=network timeout" in summary

    runner.assert_segments_failed(expected_failures)


def test_process_budget_variance_marks_remaining_segments_as_skipped_on_exception() -> None:
    rows = [make_row(record_no=i, description=f"Row{i}", amount=i) for i in range(1, 4)]

    run_id = "fabric-run-655"
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-655"
    submitted_at = datetime(2026, 4, 12, 15, 0, 0)

    class RaisingPlanningService:
        def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
            raise SoapSubmissionError(
                "network timeout",
                request_payload="<request>payload</request>",
            )

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=RaisingPlanningService(),
    )

    with pytest.raises(RuntimeError) as excinfo:
        runner.run_process_budget_variance(run_id, snapshot_path)

    summary = str(excinfo.value)
    assert "failed_segments=1" in summary
    assert "skipped_segments=2" in summary
    assert "segment=2 records=1 range=2-2 status=Skipped" in summary
    assert "segment=3 records=1 range=3-3 status=Skipped" in summary


def test_process_budget_variance_failure_summary_includes_all_failed_segments() -> None:
    rows = [make_row(record_no=i, description=f"Row{i}", amount=i) for i in range(1, 7)]

    run_id = "fabric-run-555"
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-555"
    submitted_at = datetime(2026, 4, 12, 16, 0, 0)
    planning_service = FakePlanningService(
        response={
            "order_no": None,
            "http_status": 400,
            "message": "bad row",
        }
    )

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=planning_service,
    )

    with pytest.raises(RuntimeError) as excinfo:
        runner.run_process_budget_variance(run_id, snapshot_path)

    summary = str(excinfo.value)
    assert "failed_segments=6" in summary
    assert "segment=1" in summary
    assert "segment=6" in summary
    assert "segment=5" in summary
    assert "... +1 more" not in summary


def test_process_budget_variance_failure_summary_does_not_truncate_message() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    run_id = "fabric-run-556"
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-556"
    submitted_at = datetime(2026, 4, 12, 16, 30, 0)
    planning_service = FakePlanningService(
        response={
            "order_no": None,
            "http_status": 400,
            "message": "x" * 5000,
        }
    )

    runner = ApplicationRunner.build(
        rows=[row1],
        version=version,
        batch=batch,
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=planning_service,
    )

    with pytest.raises(RuntimeError) as excinfo:
        runner.run_process_budget_variance(run_id, snapshot_path)

    summary = str(excinfo.value)
    assert "x" * 5000 in summary
    assert "(truncated)" not in summary


def test_process_budget_variance_applies_retention_when_configured() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    rows = [row1]

    run_id = "fabric-run-321"
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-321"
    submitted_at = datetime(2026, 4, 12, 15, 0, 0)
    segment_monitor = FakeSegmentMonitor()

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        submitted_at=submitted_at,
        segment_monitor_retention_days=14,
        segment_monitor=segment_monitor,
    )

    runner.run_process_budget_variance(run_id, snapshot_path)

    runner.assert_retention_applied(
        [
            {
                "retention_days": 14,
                "now_utc": submitted_at,
            }
        ]
    )


def test_process_budget_variance_continues_when_retention_fails() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    rows = [row1]

    run_id = "fabric-run-333"
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-333"
    submitted_at = datetime(2026, 4, 12, 15, 30, 0)
    messages: list[str] = []
    segment_monitor = FakeSegmentMonitor(retention_error=RuntimeError("cleanup failed"))

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        submitted_at=submitted_at,
        segment_monitor_retention_days=14,
        segment_monitor=segment_monitor,
        log_fn=messages.append,
    )

    runner.run_process_budget_variance(run_id, snapshot_path)

    assert any("Retention cleanup warning" in message for message in messages)
    assert runner.segment_monitor.submissions


class FakeFailedRequestFileSystem:
    def __init__(self) -> None:
        self.mkdirs_calls: list[str] = []
        self.put_calls: list[tuple[str, str, bool]] = []

    def mkdirs(self, path: str) -> None:
        self.mkdirs_calls.append(path)

    def put(self, path: str, text: str, overwrite: bool) -> None:
        self.put_calls.append((path, text, overwrite))


def test_process_budget_variance_saves_failed_request_payload_for_failed_segment() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    run_id = "fabric-run-700"
    snapshot_path = "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/plan_data_sample.json"
    submitted_at = datetime(2026, 4, 12, 17, 0, 0)
    planning_service = FakePlanningService(
        response={
            "order_no": None,
            "http_status": 400,
            "message": "bad row",
            "request_payload": "<soap>request</soap>",
        }
    )
    failed_request_fs = FakeFailedRequestFileSystem()

    runner = ApplicationRunner.build(
        rows=[row1],
        version="ADJ",
        batch="WKD",
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=planning_service,
        failed_request_fs=failed_request_fs,
    )

    with pytest.raises(RuntimeError):
        runner.run_process_budget_variance(run_id, snapshot_path)

    assert failed_request_fs.mkdirs_calls == [
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/failed_requests"
    ]
    assert len(failed_request_fs.put_calls) == 1
    file_path, payload, overwrite = failed_request_fs.put_calls[0]
    assert file_path.endswith("_fabric-run-700_segment_1.xml")
    assert payload == "<soap>request</soap>"
    assert overwrite is True


def test_process_budget_variance_saves_failed_request_payload_on_exception() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    run_id = "fabric-run-701"
    snapshot_path = "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/plan_data_sample.json"
    submitted_at = datetime(2026, 4, 12, 17, 30, 0)
    failed_request_fs = FakeFailedRequestFileSystem()

    class RaisingPlanningService:
        def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
            raise SoapSubmissionError(
                "network timeout",
                request_payload="<soap>request-exception</soap>",
            )

    runner = ApplicationRunner.build(
        rows=[row1],
        version="ADJ",
        batch="WKD",
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=RaisingPlanningService(),
        failed_request_fs=failed_request_fs,
    )

    with pytest.raises(RuntimeError):
        runner.run_process_budget_variance(run_id, snapshot_path)

    assert failed_request_fs.mkdirs_calls == [
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/failed_requests"
    ]
    assert len(failed_request_fs.put_calls) == 1
    file_path, payload, overwrite = failed_request_fs.put_calls[0]
    assert file_path.endswith("_fabric-run-701_segment_1.xml")
    assert payload == "<soap>request-exception</soap>"
    assert overwrite is True
