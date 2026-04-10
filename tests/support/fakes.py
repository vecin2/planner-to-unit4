from typing import Any


class FakePlanningService:
    def __init__(self) -> None:
        self.batches: list[list[dict]] = []

    def send_batch(self, batch: list[dict]) -> dict[str, Any]:
        self.batches.append(batch)
        return {"job_id": "fake-job", "status": "SUBMITTED"}
