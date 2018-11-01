from typing import Callable, Coroutine, TypeVar
from unittest import TestCase

class AsyncHTTPTestCase(TestCase):
    def get_url(self, path: str) -> str: ...

# TODO
T = TypeVar('T')
def gen_test(func: T) -> T: ... # -> Callable[[object], Coroutine[object, object, None]]: ...
