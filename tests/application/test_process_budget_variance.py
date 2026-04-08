from tests.support.application_runner import ApplicationRunner

def sample_plan_data_ndjson() -> str:
    return (
        '{"Client":"BI","Description":"Transportation","Account":"95020","Dim2":"A1669","Dim3":"null","Dim4":"B101956","Dim6":"C100475","Dim7":"ROM","Currency":"USD","Period":"202610","CurAmount":"12.8624"}\n'
        '{"Client":"BI","Description":"Transportation","Account":"95020","Dim2":"A1669","Dim3":"null","Dim4":"B101956","Dim6":"C100475","Dim7":"ROM","Currency":"USD","Period":"202611","CurAmount":"12.8624"}'
    )


def test_process_budget_updates_creates_archive_snapshot_for_run(tmp_path) -> None:
    source_file = tmp_path / "Files" / "FPA_Ingestion_Test" / "landing" / "Plan_Data.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(sample_plan_data_ndjson())
    snapshot_root_path = tmp_path / "Files" / "FPA_Ingestion_Test" / "snapshots"
    run_id = "fabric-run-123"

    runner = ApplicationRunner(
        source_path=str(source_file),
        snapshot_root_path=str(snapshot_root_path),
    )

    result = runner.run_process_budget_variance(run_id)

    runner.assert_archive_created_for(run_id)
    assert result.snapshot_path is not None
