from typing import Protocol, Any


class PlanningService(Protocol):
    def send_batch(self, batch: list[dict]) -> dict[str, Any]:
        """Send a batch of budget variance rows to the planning service."""
        ...
