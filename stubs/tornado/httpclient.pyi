from typing import Optional

class AsyncHTTPClient:
    async def fetch(self, request: str, raise_error: bool = ...,
                    **kwargs: object) -> HTTPResponse: ...

class HTTPResponse:
    code: int
    error: Optional[Exception]

class HTTPClientError(Exception): ...
