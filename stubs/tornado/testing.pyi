from typing import Callable, Coroutine, TypeVar
from unittest import TestCase

T = TypeVar('T')

class AsyncTestCase(TestCase): ...

class AsyncHTTPTestCase(AsyncTestCase):
    def get_url(self, path: str) -> str: ...

def gen_test(func: Callable[[T], Coroutine[object, object, None]]) -> Callable[[T], None]: ...
