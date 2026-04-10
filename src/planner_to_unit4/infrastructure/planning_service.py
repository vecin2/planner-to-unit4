from typing import Protocol

BatchSubmissionResult = dict[str, str | int | None]


class PlanningService(Protocol):
    def send_batch(self, batch: list[dict]) -> BatchSubmissionResult:
        """Send a batch of budget variance rows to the planning service."""
        ...
