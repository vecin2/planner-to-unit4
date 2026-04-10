from tests.support.application_runner import ApplicationRunner
from tests.support.fake_budget_variance_reader import FakeBudgetVarianceReader


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


def test_process_budget_variance_submits_one_batch_for_outbound_rows() -> None:
    row1 = make_row(description="Row1", amount=10)
    row2 = make_row(description="Row2", amount=20)

    rows = [row1, row2]

    run_id = "fabric-run-123"
    max_batch_size = 3

    expected_batches = [
        [row1, row2]
    ]

    budget_variance_reader = FakeBudgetVarianceReader()
    budget_variance_reader.set_rows(rows)

    runner = ApplicationRunner(
        budget_variance_reader=budget_variance_reader,
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

    expected_batches = [
        [row1, row2],
        [row3]
    ]

    budget_variance_reader = FakeBudgetVarianceReader()
    budget_variance_reader.set_rows(rows)

    runner = ApplicationRunner(
        budget_variance_reader=budget_variance_reader,
        max_batch_size=max_batch_size,
    )

    result = runner.run_process_budget_variance(run_id)
    runner.assert_batches_sent(expected_batches)
