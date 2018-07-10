# NOTE tornado 5 brings type annotations for some stuff :)

from typing import Dict, Sequence, Tuple, Type, Union, TypeVar

Handler = Union[Tuple[str, Type[RequestHandler]], Tuple[str, Type[RequestHandler], Dict[str, object]]]

class Application:
    settings: Dict[str, object]

    def __init__(self, handlers: Sequence[Handler], **settings: object) -> None: ...

class RequestHandler:
    application: Application
    current_user: object

    def write(self, chunk: Union[str, Dict[str, object]]) -> None: ...

    def set_header(self, name: str, value: str) -> None: ...

    def flush(self) -> None: ...

class StaticFileHandler(RequestHandler): ...

class HTTPError(Exception): ...

F = TypeVar('F')
def asynchronous(method: F) -> F: ...
