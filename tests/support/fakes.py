class FakePlanningService:
    def __init__(self) -> None:
        self.batches: list[list[dict]] = []

    def send_batch(self, batch: list[dict]) -> dict[str, str | int | None]:
        self.batches.append(batch)
        return {
            "status": "SUBMITTED",
            "order_no": "fake-order",
            "http_status": 200,
            "message": None,
        }
