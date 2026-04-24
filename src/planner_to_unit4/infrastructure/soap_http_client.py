from typing import Callable, Protocol


class HttpResponse(Protocol):
    status_code: int
    text: str


HttpPost = Callable[[str, bytes, dict[str, str], int], HttpResponse]
