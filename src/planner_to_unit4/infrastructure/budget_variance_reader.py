from typing import Protocol, List


class BudgetVarianceReader(Protocol):
    def read_rows(self) -> List[dict]:
        """Read budget variance rows from the source (Spark table or test fake)."""
        ...
