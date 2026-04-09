from typing import List,Any



class FakePlanningService:
    def __init__(self) -> None:
        self.batches: List[List[Any]] = []

    def send_batch(self, batch: List[List[Any]]):
        self.batches.append(batch)
        return {"job_id": "fake-job", "status": "SUBMITTED"}
