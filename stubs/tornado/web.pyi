from typing import Dict, Optional, Sequence, Tuple, Type, Union

class RequestHandler:
    application: Application
    current_user: Optional[object]

    def write(self, chunk: Union[bytes, str, Dict[str, object]]) -> None: ...

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
