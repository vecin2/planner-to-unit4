from tests.support.application_runner import ApplicationRunner
import json

def sample_plan_data_ndjson() -> str:
    return (
        '{"Client":"BI","Description":"Transportation","Account":"95020","Dim2":"A1669","Dim3":"null","Dim4":"B101956","Dim6":"C100475","Dim7":"ROM","Currency":"USD","Period":"202610","CurAmount":"12.8624"}\n'
        '{"Client":"BI","Description":"Transportation","Account":"95020","Dim2":"A1669","Dim3":"null","Dim4":"B101956","Dim6":"C100475","Dim7":"ROM","Currency":"USD","Period":"202611","CurAmount":"12.8624"}'
    )
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

def to_ndjson(rows):
    return "\n".join(json.dumps(r) for r in rows)

def test_process_budget_variance_submits_one_batch_for_outbound_rows(tmp_path) -> None:
    source_file = tmp_path / "Files" / "FPA_Ingestion_Test" / "landing" / "Plan_Data.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)

    row1 = make_row(description="Row1", amount=10)
    row2 = make_row(description="Row2", amount=20)

    rows = [row1, row2]

    source_file.write_text(to_ndjson(rows))#sample_plan_data_ndjson())
    snapshot_root_path = tmp_path / "Files" / "FPA_Ingestion_Test" / "snapshots"
    run_id = "fabric-run-123"

    max_batch_size = 3  # Set batch size large enough to fit both rows in one batch
    expected_batches = [
        [row1, row2]  # Both rows should be in a single batch
    ]

    runner = ApplicationRunner(
        source_path=str(source_file),
        snapshot_root_path=str(snapshot_root_path),
        max_batch_size=max_batch_size,
    )

    result = runner.run_process_budget_variance(run_id)
    runner.assert_batches_sent(expected_batches)

    runner.assert_archive_created_for(run_id)
    assert result.snapshot_path is not None


def test_process_budget_variance_submits_multiple_batches_when_batch_size_is_small(tmp_path) -> None:
    source_file = tmp_path / "Files" / "FPA_Ingestion_Test" / "landing" / "Plan_Data.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)

    row1 = make_row(description="Row1", amount=10)
    row2 = make_row(description="Row2", amount=20)
    row3 = make_row(description="Row3", amount=30)

    rows = [row1, row2, row3]

    source_file.write_text(to_ndjson(rows))
    snapshot_root_path = tmp_path / "Files" / "FPA_Ingestion_Test" / "snapshots"
    run_id = "fabric-run-456"

    max_batch_size = 2  # Set batch size smaller than number of rows
    expected_batches = [
        [row1, row2],  # First batch with 2 rows
        [row3]         # Second batch with remaining row
    ]

    runner = ApplicationRunner(
        source_path=str(source_file),
        snapshot_root_path=str(snapshot_root_path),
        max_batch_size=max_batch_size,
    )

    result = runner.run_process_budget_variance(run_id)
    runner.assert_batches_sent(expected_batches)

    runner.assert_archive_created_for(run_id)
    assert result.snapshot_path is not None
