from typing import Dict, Sequence, Tuple, Type, Union

Handler = Union[Tuple[str, Type[RequestHandler]], Tuple[str, Type[RequestHandler], Dict[str, object]]]

class Application:
    settings: Dict[str, object]

    def __init__(self, handlers: Sequence[Handler], **settings: object) -> None: ...

class RequestHandler:
    application: Application
    current_user: object

    def write(self, chunk: Dict[str, object]) -> None: ...

class StaticFileHandler(RequestHandler): ...

class HTTPError(Exception): ...
