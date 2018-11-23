from typing import Callable, Coroutine, TypeVar
from unittest import TestCase

from tornado.ioloop import IOLoop

T = TypeVar('T')

class AsyncTestCase(TestCase):
    io_loop: IOLoop

class AsyncHTTPTestCase(AsyncTestCase):
    def get_url(self, path: str) -> str: ...

def gen_test(func: Callable[[T], Coroutine[object, object, None]]) -> Callable[[T], None]: ...
