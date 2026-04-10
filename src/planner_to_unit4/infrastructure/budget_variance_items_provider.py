from __future__ import annotations

from planner_to_unit4.infrastructure.budget_variance_reader import BudgetVarianceReader


class BudgetVarianceItemsProvider:
    def __init__(self, reader: BudgetVarianceReader, version: str, batch: str) -> None:
        self.reader = reader
        self.version = version
        self.batch = batch

    def read_items(self) -> list[dict]:
        rows = self.reader.read_rows()
        enriched = []
        for row in rows:
            item = dict(row)
            item["Version"] = self.version
            item["Batch"] = self.batch
            enriched.append(item)
        return enriched
