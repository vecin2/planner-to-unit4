from planner_to_unit4.entrypoints import submit_budget_variance


def test_submit_budget_variance_passes_max_records(monkeypatch) -> None:
    captured = {}

    class FakeReader:
        def __init__(self, spark, table_name: str, max_records: int | None = None) -> None:
            captured["spark"] = spark
            captured["table_name"] = table_name
            captured["max_records"] = max_records

    def fake_planning_service(**kwargs):
        return "planning"

    def fake_segment_monitor(**kwargs):
        return "monitor"

    monkeypatch.setattr(submit_budget_variance, "SparkBudgetVarianceReader", FakeReader)
    monkeypatch.setattr(submit_budget_variance, "SoapPlanningService", fake_planning_service)
    monkeypatch.setattr(submit_budget_variance, "SparkSegmentMonitor", fake_segment_monitor)

    submit_budget_variance.main(
        spark="spark",
        source_table_name="source.table",
        version="ADJ",
        batch="WKD",
        log_fn=lambda _message: None,
        max_records=123,
        endpoint="https://example.test/service.svc",
        username="user",
        client="bi",
        password="secret",
        segment_monitoring_table="planner_to_unit4.segment_monitoring",
    )

    assert captured["max_records"] == 123
