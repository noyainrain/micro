from collections.abc import Iterable
from typing import Dict, List, Optional, Sequence, Tuple, Union, overload

from typing_extensions import Literal

from .connection import ConnectionPool

_Key = Union[str, bytes]
_Value = Union[bytes, float, int, str]

class Redis:
    connection_pool: ConnectionPool

    def __init__(self, host: str = ..., port: int = ..., db: int = ...) -> None: ...

    @classmethod
    def from_url(cls, url: str, db: int = None) -> Redis: ...

    def config_get(self, pattern: str = ...) -> Dict[str, str]: ...

    def config_set(self, name: str, value: str) -> None: ...

    def delete(self, *names: str) -> int: ...

    def get(self, name: _Key) -> Optional[bytes]: ...

    def hget(self, name: _Key, key: _Key) -> bytes | None: ...

    def hset(self, name: _Key, key: _Key, value: _Value) -> int: ...

    def lindex(self, name: str, index: int) -> Optional[bytes]: ...

    def llen(self, name: str) -> int: ...

    def lrange(self, name: str, start: int, end: int) -> List[bytes]: ...

    def lrem(self, name: str, count: int, value: bytes) -> int: ...

    def pubsub(self) -> PubSub: ...

    def register_script(self, script: str) -> Script: ...

    def rpush(self, name: _Key, *values: _Value) -> int: ...

    def sismember(self, name: _Key, value: _Value) -> bool: ...

    def zadd(self, name: _Key, mapping: dict[_Key, float]) -> int: ...

    def zcard(self, name: str) -> int: ...

    @overload
    def zrange(self, name: str, start: int, end: int, *,
               withscores: Literal[False] = ...) -> List[bytes]: ...
    @overload
    def zrange(self, name: str, start: int, end: int, *,
               withscores: Literal[True]) -> List[Tuple[bytes, float]]: ...

    def zrangebyscore(self, name: str, min: float, max: float) -> List[bytes]: ...

    def zrank(self, name: str, value: bytes) -> int: ...

    def zrem(self, name: str, *values: bytes) -> int: ...

    def zscore(self, name: str, value: bytes) -> float: ...

StrictRedis = Redis

class PubSub:
    def close(self) -> None: ...

    def subscribe(self, *args: str) -> None: ...

    def get_message(self, ignore_subscribe_messages: bool = ...,
                    timeout: float = ...) -> Optional[Dict[str, object]]: ...

class Script:
    # Return type is recursive
    def __call__(self, keys: Iterable[_Key] = ..., args: Iterable[_Value] = ...): ...
