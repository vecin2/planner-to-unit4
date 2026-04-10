class FakeBudgetVarianceItemsProvider:
    def __init__(self) -> None:
        self._items: list[dict] = []

    def set_items(self, items: list[dict]) -> None:
        self._items = items

    def read_items(self) -> list[dict]:
        return self._items
