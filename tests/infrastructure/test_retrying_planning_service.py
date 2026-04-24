import pytest

from planner_to_unit4.infrastructure.retrying_planning_service import RetryingPlanningService


def test_send_segment_returns_without_retry_on_first_success() -> None:
    class SuccessfulService:
        def __init__(self) -> None:
            self.calls = 0

        def send_segment(self, segment: list[dict]) -> dict[str, object]:
            self.calls += 1
            return {"order_no": "51", "http_status": 200, "message": None}

    service = SuccessfulService()
    retrying_service = RetryingPlanningService(service=service, retries=3)

    result = retrying_service.send_segment([{"record_no": 1}])

    assert result["order_no"] == "51"
    assert service.calls == 1


def test_send_segment_retries_on_exception_then_succeeds() -> None:
    class FlakyService:
        def __init__(self) -> None:
            self.calls = 0

        def send_segment(self, segment: list[dict]) -> dict[str, object]:
            self.calls += 1
            if self.calls < 3:
                raise TimeoutError("network timeout")
            return {"order_no": "52", "http_status": 200, "message": None}

    logs: list[str] = []
    service = FlakyService()
    retrying_service = RetryingPlanningService(service=service, retries=2, log_fn=logs.append)

    result = retrying_service.send_segment([{"record_no": 1}])

    assert result["order_no"] == "52"
    assert service.calls == 3
    assert len(logs) == 2
    assert "attempt=2/3" in logs[0]
    assert "attempt=3/3" in logs[1]


def test_send_segment_raises_after_retries_exhausted() -> None:
    class AlwaysFailingService:
        def __init__(self) -> None:
            self.calls = 0

        def send_segment(self, segment: list[dict]) -> dict[str, object]:
            self.calls += 1
            raise TimeoutError("network timeout")

    service = AlwaysFailingService()
    retrying_service = RetryingPlanningService(service=service, retries=2)

    with pytest.raises(TimeoutError, match="network timeout"):
        retrying_service.send_segment([{"record_no": 1}])

    assert service.calls == 3


def test_send_segment_does_not_retry_non_exception_result() -> None:
    class FailedResponseService:
        def __init__(self) -> None:
            self.calls = 0

        def send_segment(self, segment: list[dict]) -> dict[str, object]:
            self.calls += 1
            return {
                "order_no": None,
                "http_status": 500,
                "message": "Something went wrong.",
            }

    service = FailedResponseService()
    retrying_service = RetryingPlanningService(service=service, retries=3)

    result = retrying_service.send_segment([{"record_no": 1}])

    assert result["order_no"] is None
    assert result["http_status"] == 500
    assert service.calls == 1
