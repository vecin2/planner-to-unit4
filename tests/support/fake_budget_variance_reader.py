from typing import List


class FakeBudgetVarianceReader:
    def __init__(self) -> None:
        self._rows: List[dict] = []

    def set_rows(self, rows: List[dict]) -> None:
        self._rows = rows

    def read_rows(self) -> List[dict]:
        return self._rows
