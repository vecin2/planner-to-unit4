class FakeBudgetVarianceReader:
    def __init__(self) -> None:
        self._rows: list[dict] = []

    def set_rows(self, rows: list[dict]) -> None:
        self._rows = rows

    def read_rows(self) -> list[dict]:
        return self._rows
