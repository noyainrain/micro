# TODO

import builtins
from typing import Dict, List, Tuple, Callable, Optional, cast

class Error(Exception):
    """TODO."""

    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

    def json(self) -> Dict[str, object]:
        return {'__type__': type(self).__name__, 'msg': str(self)}

class ValueError(Error, builtins.ValueError):
    """See TODO."""
    pass

class CommunicationError(Error):
    """See :ref:`CommunicationError`."""

    args = None # type: Tuple[str, str, Optional[str]]

    def __init__(self, message: str, request: str, response: str = None) -> None:
        super().__init__(message)
        self.request = request
        self.response = response

    def json(self) -> Dict[str, object]:
        return {**super().json(), 'request': self.request, 'response': self.response}
