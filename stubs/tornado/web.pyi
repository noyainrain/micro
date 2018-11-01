from typing import Dict, Optional, Sequence, Tuple, Type, Union

class RequestHandler:
    application: Application
    current_user: Optional[object]

    def set_status(self, status_code: int) -> None: ...

    def get_query_argument(self, name: str, default: str = ...) -> str: ...

    def write(self, chunk: Union[bytes, str, Dict[str, object]]) -> None: ...

    def get_template_namespace(self) -> Dict[str, object]: ...

class Application:
    settings: Dict[str, object]

    def __init__(
        self,
        handlers:
            Sequence[
                Union[Tuple[str, Type[RequestHandler]], Tuple[str, Type[RequestHandler],
                      Dict[str, object]]]] = None,
        **settings: object) -> None: ...

class StaticFileHandler(RequestHandler): ...

class HTTPError(Exception): ...
