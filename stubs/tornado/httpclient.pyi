from typing import Dict, Optional, Union

class AsyncHTTPClient:
    async def fetch(self, request: Union[HTTPRequest, str], raise_error: bool = ...,
                    **kwargs: object) -> HTTPResponse: ...

class HTTPRequest:
    url: str
    method: str

class HTTPResponse:
    code: int
    headers: Dict[str, str]
    effective_url: str
    body: bytes
    error: Optional[Exception]

class HTTPClientError(Exception):
    code: int
