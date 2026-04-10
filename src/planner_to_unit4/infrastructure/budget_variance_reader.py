from typing import Protocol


class BudgetVarianceReader(Protocol):
    def read_rows(self) -> list[dict]:
        """Read budget variance rows from the source (Spark table or test fake)."""
        ...
