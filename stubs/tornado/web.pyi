from asyncio import Future
import datetime
from numbers import Integral
from typing import Dict, Optional, Sequence, Tuple, Type, Union

from .httputil import HTTPServerRequest

_HeaderTypes = Union[bytes, str, int, Integral, datetime.datetime]

class RequestHandler:
    request: HTTPServerRequest
    application: Application
    current_user: Optional[object]

    def set_status(self, status_code: int) -> None: ...

    def set_header(self, name: str, value: _HeaderTypes) -> None: ...

    def get_query_argument(self, name: str, default: str = ...) -> str: ...

    def write(self, chunk: Union[bytes, str, Dict[str, object]]) -> None: ...

    def get_template_namespace(self) -> Dict[str, object]: ...

    def flush(self, include_footers: bool = ...) -> Future[None]: ...

class Application:
    settings: Dict[str, object]

    def __init__(
        self,
        handlers:
            Sequence[
                Union[Tuple[str, Type[RequestHandler]], Tuple[str, Type[RequestHandler],
                      Dict[str, object]]]],
        **settings: object) -> None: ...

class StaticFileHandler(RequestHandler): ...

class HTTPError(Exception): ...
