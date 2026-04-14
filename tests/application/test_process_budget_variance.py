from datetime import datetime

import pytest

from tests.support.application_runner import ApplicationRunner
from tests.support.fakes import FakePlanningService


def make_row(
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
    row1 = make_row(description="Row1", amount=10)
    row2 = make_row(description="Row2", amount=20)

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
    row1 = make_row(description="Row1", amount=10)
    row2 = make_row(description="Row2", amount=20)
    row3 = make_row(description="Row3", amount=30)

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
    row1 = make_row(description="Row1", amount=10)

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

    with pytest.raises(RuntimeError, match="Budget variance submission failed for 1 segments"):
        runner.run_process_budget_variance(run_id, snapshot_path)

    runner.assert_segments_failed(expected_failures)


def test_process_budget_variance_records_failed_segment_for_non_200() -> None:
    row1 = make_row(description="Row1", amount=10)

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

    with pytest.raises(RuntimeError, match="Budget variance submission failed for 1 segments"):
        runner.run_process_budget_variance(run_id, snapshot_path)

    runner.assert_segments_failed(expected_failures)


def test_process_budget_variance_records_failed_segment_on_exception() -> None:
    row1 = make_row(description="Row1", amount=10)

    rows = [row1]

    run_id = "fabric-run-654"
    max_segment_size = 2
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-654"
    submitted_at = datetime(2026, 4, 12, 14, 30, 0)

    class RaisingPlanningService:
        def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
            raise TimeoutError("network timeout")

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

    with pytest.raises(TimeoutError, match="network timeout"):
        runner.run_process_budget_variance(run_id, snapshot_path)

    runner.assert_segments_failed(expected_failures)
