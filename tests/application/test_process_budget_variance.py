from tests.support.application_runner import ApplicationRunner


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


def test_process_budget_variance_submits_one_batch_for_outbound_rows() -> None:
    row1 = make_row(description="Row1", amount=10)
    row2 = make_row(description="Row2", amount=20)

    rows = [row1, row2]

    run_id = "fabric-run-123"
    max_batch_size = 3
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-123"
    expected_batches = [
        [
            with_version_and_batch(row1, version, batch),
            with_version_and_batch(row2, version, batch),
        ]
    ]

    runner = ApplicationRunner(
        rows=rows,
        version=version,
        batch=batch,
        snapshot_path=snapshot_path,
        max_batch_size=max_batch_size,
    )

    result = runner.run_process_budget_variance(run_id)
    runner.assert_batches_sent(expected_batches)


def test_process_budget_variance_submits_multiple_batches_when_batch_size_is_small() -> None:
    row1 = make_row(description="Row1", amount=10)
    row2 = make_row(description="Row2", amount=20)
    row3 = make_row(description="Row3", amount=30)

    rows = [row1, row2, row3]

    run_id = "fabric-run-456"
    max_batch_size = 2
    version = "ADJ"
    batch = "WKD"
    snapshot_path = "snapshot-456"
    expected_batches = [
        [
            with_version_and_batch(row1, version, batch),
            with_version_and_batch(row2, version, batch),
        ],
        [with_version_and_batch(row3, version, batch)]
    ]

    runner = ApplicationRunner(
        rows=rows,
        version=version,
        batch=batch,
        snapshot_path=snapshot_path,
        max_batch_size=max_batch_size,
    )

    result = runner.run_process_budget_variance(run_id)
    runner.assert_batches_sent(expected_batches)
