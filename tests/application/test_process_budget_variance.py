from datetime import datetime

from planner_to_unit4.infrastructure.planning_service import ResolvedPostbackError
from planner_to_unit4.infrastructure.soap_planning_service import SoapSubmissionError
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

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)
    assert outcome.status == "COMPLETED"
    assert outcome.is_success() is True
    assert outcome.is_failed() is False
    assert outcome.failed_segments == 0
    assert outcome.email_html_body == ""
    assert outcome.summary_text == "COMPLETED | failed=0 skipped=0 total=1"
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

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)
    assert outcome.status == "COMPLETED"
    assert outcome.summary_text == "COMPLETED | failed=0 skipped=0 total=2"
    runner.assert_segments_sent(expected_segments)
    runner.assert_segments_submitted(expected_submissions)


def test_process_budget_variance_payload_has_stable_keys_for_success_and_failure() -> None:
    success_runner = ApplicationRunner.build(
        rows=[make_row(record_no=1, description="Row1", amount=10)],
        version="ADJ",
        batch="WKD",
        max_segment_size=1,
        submitted_at=datetime(2026, 4, 12, 12, 45, 0),
    )
    success_outcome = success_runner.run_process_budget_variance(
        "fabric-run-success",
        "snapshot-success",
    )

    failure_runner = ApplicationRunner.build(
        rows=[make_row(record_no=1, description="Row1", amount=10)],
        version="ADJ",
        batch="WKD",
        max_segment_size=1,
        submitted_at=datetime(2026, 4, 12, 12, 46, 0),
        planning_service=FakePlanningService(
            response={
                "order_no": None,
                "http_status": 400,
                "message": "bad row",
            }
        ),
    )
    failure_outcome = failure_runner.run_process_budget_variance(
        "fabric-run-failure",
        "snapshot-failure",
    )

    success_payload = success_outcome.to_payload()
    failure_payload = failure_outcome.to_payload()

    assert set(success_payload) == set(failure_payload)
    assert success_payload["status"] == "COMPLETED"
    assert failure_payload["status"] == "FAILED"


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
    normalized_failure_message = "Validation errors returned in postback log items."
    planning_service = FakePlanningService(
        response={
            "order_no": None,
            "http_status": 200,
            "message": failure_message,
            "resolved_errors": [
                ResolvedPostbackError(
                    row_index_1_based=2,
                    column="dim_3",
                    message="B102397 is not a legal RESNO",
                    failed_row=None,
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
        message=normalized_failure_message,
    )

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert outcome.is_success() is False
    assert outcome.is_failed() is True
    assert "<html lang='en'>" in outcome.email_html_body
    assert (
        outcome.summary_text == "FAILED | failed=1 skipped=0 total=1 "
        f"| reason={normalized_failure_message}"
    )

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

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert (
        outcome.summary_text == "FAILED | failed=1 skipped=0 total=1 | reason=Something went wrong."
    )

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

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert outcome.error_type == "SoapSubmissionError"
    assert outcome.error_message == "network timeout"
    assert outcome.summary_text == "FAILED | failed=1 skipped=0 total=1 | reason=network timeout"

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

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert outcome.summary_text == "FAILED | failed=1 skipped=2 total=3 | reason=network timeout"


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

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert outcome.summary_text == "FAILED | failed=6 skipped=0 total=6 | reason=bad row"


def test_process_budget_variance_summary_uses_multiple_reason_for_mixed_failures() -> None:
    rows = [make_row(record_no=i, description=f"Row{i}", amount=i) for i in range(1, 3)]

    run_id = "fabric-run-557"
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-557"
    submitted_at = datetime(2026, 4, 12, 16, 15, 0)

    class SequencedPlanningService:
        def __init__(self) -> None:
            self._responses = [
                {
                    "order_no": None,
                    "http_status": 500,
                    "message": "Something went wrong.",
                },
                {
                    "order_no": None,
                    "http_status": 400,
                    "message": "Validation errors returned in postback log items.",
                    "resolved_errors": [
                        ResolvedPostbackError(
                            row_index_1_based=1,
                            column="dim_2",
                            message="Dim2 cannot be null",
                            failed_row={"record_no": 2},
                        )
                    ],
                },
            ]
            self._index = 0

        def send_segment(self, segment: list[dict]) -> dict[str, str | int | None | list]:
            response = self._responses[self._index]
            self._index += 1
            return dict(response)

    runner = ApplicationRunner.build(
        rows=rows,
        version=version,
        batch=batch,
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=SequencedPlanningService(),
    )

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert (
        outcome.summary_text
        == "FAILED | failed=2 skipped=0 total=2 | reason=Multiple segment failures"
    )


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

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert outcome.summary_text == f"FAILED | failed=1 skipped=0 total=1 | reason={'x' * 5000}"


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


class FakeArtifactFileSystem:
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
    artifact_fs = FakeArtifactFileSystem()

    runner = ApplicationRunner.build(
        rows=[row1],
        version="ADJ",
        batch="WKD",
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=planning_service,
        artifact_fs=artifact_fs,
    )

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"

    assert artifact_fs.mkdirs_calls == [
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/requests",
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/reports",
    ]
    assert len(artifact_fs.put_calls) == 2
    file_path, payload, overwrite = artifact_fs.put_calls[0]
    assert file_path.endswith("_fabric-run-700_segment_1_failed.xml")
    assert payload == "<soap>request</soap>"
    assert overwrite is True
    report_path, _report_payload, report_overwrite = artifact_fs.put_calls[1]
    assert report_path.endswith("_fabric-run-700_failed.html")
    assert report_overwrite is True


def test_process_budget_variance_saves_failed_request_payload_on_exception() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    run_id = "fabric-run-701"
    snapshot_path = "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/plan_data_sample.json"
    submitted_at = datetime(2026, 4, 12, 17, 30, 0)
    artifact_fs = FakeArtifactFileSystem()

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
        artifact_fs=artifact_fs,
    )

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"

    assert artifact_fs.mkdirs_calls == [
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/requests",
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/reports",
    ]
    assert len(artifact_fs.put_calls) == 2
    file_path, payload, overwrite = artifact_fs.put_calls[0]
    assert file_path.endswith("_fabric-run-701_segment_1_failed.xml")
    assert payload == "<soap>request-exception</soap>"
    assert overwrite is True


def test_process_budget_variance_artifact_save_mode_always_saves_success_artifacts() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    run_id = "fabric-run-702"
    snapshot_path = "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/plan_data_sample.json"
    submitted_at = datetime(2026, 4, 12, 18, 0, 0)
    planning_service = FakePlanningService(
        response={
            "order_no": "ok-order-1",
            "http_status": 200,
            "message": None,
            "request_payload": "<soap>request-success</soap>",
        }
    )
    artifact_fs = FakeArtifactFileSystem()

    runner = ApplicationRunner.build(
        rows=[row1],
        version="ADJ",
        batch="WKD",
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=planning_service,
        artifact_fs=artifact_fs,
        artifact_save_mode="always",
    )

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "COMPLETED"
    assert outcome.report_html_path is not None
    assert outcome.report_html_path.endswith(".html")

    assert artifact_fs.mkdirs_calls == [
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/requests",
        "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/reports",
    ]
    assert len(artifact_fs.put_calls) == 2
    request_path, request_payload, request_overwrite = artifact_fs.put_calls[0]
    assert request_path.endswith("_fabric-run-702_segment_1_submitted.xml")
    assert request_payload == "<soap>request-success</soap>"
    assert request_overwrite is True
    report_path, report_payload, report_overwrite = artifact_fs.put_calls[1]
    assert report_path.endswith("_fabric-run-702_completed.html")
    assert "Planner Upload Result" in report_payload
    assert "Order No: <strong style='color:#1f2937;'>ok-order-1</strong>" in report_payload
    assert report_overwrite is True


def test_process_budget_variance_artifact_save_mode_never_skips_artifacts() -> None:
    row1 = make_row(record_no=1, description="Row1", amount=10)

    run_id = "fabric-run-703"
    snapshot_path = "Files/FPA_Ingestion_Test/archive/yyyy=2026/mm=04/dd=20/plan_data_sample.json"
    submitted_at = datetime(2026, 4, 12, 18, 30, 0)
    planning_service = FakePlanningService(
        response={
            "order_no": None,
            "http_status": 400,
            "message": "bad row",
            "request_payload": "<soap>request</soap>",
        }
    )
    artifact_fs = FakeArtifactFileSystem()

    runner = ApplicationRunner.build(
        rows=[row1],
        version="ADJ",
        batch="WKD",
        max_segment_size=1,
        submitted_at=submitted_at,
        planning_service=planning_service,
        artifact_fs=artifact_fs,
        artifact_save_mode="never",
    )

    outcome = runner.run_process_budget_variance(run_id, snapshot_path)

    assert outcome.status == "FAILED"
    assert outcome.report_html_path is None
    assert artifact_fs.mkdirs_calls == []
    assert artifact_fs.put_calls == []
