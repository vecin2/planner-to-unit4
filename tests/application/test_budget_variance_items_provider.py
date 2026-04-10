from planner_to_unit4.application.budget_variance_items_provider import (
    DefaultBudgetVarianceItemsProvider,
)
from tests.support.fake_budget_variance_reader import FakeBudgetVarianceReader


def test_items_provider_enriches_rows_with_version_and_batch() -> None:
    reader = FakeBudgetVarianceReader()
    reader.set_rows(
        [
            {
                "Client": "BI",
                "Description": "Test",
                "Account": "1000",
                "Dim2": "A1",
                "Dim3": "X",
                "Dim4": "B1",
                "Dim6": "C1",
                "Dim7": "ROM",
                "Currency": "USD",
                "Period": "202601",
                "CurAmount": 12.25,
            }
        ]
    )

    provider = DefaultBudgetVarianceItemsProvider(reader, version="ADJ", batch="WKD")
    items = provider.read_items()

    assert items[0]["Version"] == "ADJ"
    assert items[0]["Batch"] == "WKD"
