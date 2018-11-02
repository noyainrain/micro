from typing import Dict, Optional

class AsyncHTTPClient:
    async def fetch(self, request: str, raise_error: bool = ...,
                    **kwargs: object) -> HTTPResponse: ...

class HTTPResponse:
    code: int
    headers: Dict[str, str]
    effective_url: str
    body: bytes
    error: Optional[Exception]

class HTTPClientError(Exception):
    code: int
