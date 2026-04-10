from typing import Protocol


class HttpResponse(Protocol):
    status_code: int
    text: str


class HttpPost(Protocol):
    def __call__(
        self,
        url: str,
        data: str,
        headers: dict[str, str],
        timeout: int,
    ) -> HttpResponse: ...
