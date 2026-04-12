class FakePlanningService:
    def __init__(self) -> None:
        self.segments: list[list[dict]] = []

    def send_segment(self, segment: list[dict]) -> dict[str, str | int | None]:
        self.segments.append(segment)
        return {
            "status": "SUBMITTED",
            "order_no": "fake-order",
            "http_status": 200,
            "message": None,
        }
