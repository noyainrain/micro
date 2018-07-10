# jsonredis
# https://github.com/NoyaInRain/micro/blob/master/jsonredis.py
# part of Micro
# released into the public domain

"""Extended :class:`Redis` client for convinient use with JSON objects.

Also includes :class:`JSONRedisMapping`, an utility map interface for JSON objects.
"""

import json
from typing import (Callable, Dict, Generic, List, Mapping, Optional, Sequence, Type, TypeVar,
                    Union, cast, overload)
from weakref import WeakValueDictionary

from redis import StrictRedis
from redis.exceptions import ResponseError

T = TypeVar('T')
U = TypeVar('U')

class JSONRedis(Generic[T]):
    """Extended :class:`Redis` client for convenient use with JSON objects.

    Objects are stored as JSON-encoded strings in the Redis database and en-/decoding is handled
    transparently.

    The translation from an arbitrary object to a JSON-serializable form is carried out by a given
    ``encode(object)`` function. A JSON-serializable object is one that only cosists of the types
    given in https://docs.python.org/3/library/json.html#py-to-json-table . *encode* is passed as
    *default* argument to :func:`json.dumps()`.

    The reverse translation is done by a given ``decode(json)`` function. *decode* is passed as
    *object_hook* argument to :func:`json.loads()`.

    When *caching* is enabled, objects loaded from the Redis database are cached and subsequently
    retrieved from the cache. An object stays in the cache as long as there is a reference to it and
    it is automatically removed when the Python interpreter destroys it. Thus, it is guaranteed that
    getting the same key multiple times will yield the identical object.

    .. attribute:: r

       Underlying :class:`Redis` client.

    .. attribute:: encode

       Function to encode an object to a JSON-serializable form.

    .. attribute:: decode

       Function to decode an object from a JSON-serializable form.

    .. attribute:: caching

        Switch to enable / disable object caching.
    """

    def __init__(
            self, r: StrictRedis, encode: Callable[[T], Dict[str, object]] = None,
            decode: Callable[[Dict[str, object]], Union[T, Dict[str, object]]] = None,
            caching: bool = True) -> None:
        self.r = r
        self.encode = encode
        self.decode = decode
        self.caching = caching
        self._cache = WeakValueDictionary() # type: WeakValueDictionary[str, T]
        # pylint: disable=undefined-variable

    @overload
    def oget(self, key: str) -> Optional[T]:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    @overload
    def oget(self, key: str, default: Type[Exception]) -> T:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    @overload
    def oget(self, key: str, default: Type[Exception], expect: Callable[[T], U]) -> U:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    @overload
    def oget(self, key: str, default: None, expect: Callable[[T], U]) -> Optional[U]:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    def oget(self, key: str, default: Type[Exception] = None,
             expect: Callable[[T], U] = None) -> Union[Optional[T], T, U, Optional[U]]:
        """Return the object at *key*."""
        # pylint: disable=function-redefined; overload
        object = self._cache.get(key) if self.caching else None
        if object is None:
            value = cast(Optional[bytes], self.get(key))
            if value is not None:
                if not value.startswith(b'{'):
                    raise ResponseError()
                try:
                    # Unfortunately we cannot eliminate dict here, because it could be valid in T
                    object = cast(T, json.loads(value.decode(), object_hook=self.decode))
                except ValueError:
                    raise ResponseError()
                if self.caching:
                    self._cache[key] = object
        if object is None:
            if default is not None and issubclass(default, Exception):
                raise default(key)
            object = default
        return expect(object) if expect and object is not None else object

    def oset(self, key: str, object: T) -> None:
        """Set *key* to hold *object*."""
        if self.caching:
            self._cache[key] = object
        self.set(key, json.dumps(object, default=self.encode))

    @overload
    def omget(self, keys: List[str]) -> List[Optional[T]]:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    @overload
    def omget(self, keys: List[str], default: Type[Exception]) -> List[T]:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    @overload
    def omget(self, keys: List[str], default: Type[Exception], expect: Callable[[T], U]) -> List[U]:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    @overload
    def omget(self, keys: List[str], default: None, expect: Callable[[T], U]) -> List[Optional[U]]:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    def omget(
            self, keys: List[str], default: Type[Exception] = None, expect: Callable[[T], U] = None
        ) -> Union[List[Optional[T]], List[T], List[U], List[Optional[U]]]:
        """Return a list of objects for the given *keys*."""
        # pylint: disable=function-redefined; overload
        # NOTE: Not atomic at the moment
        if default and expect:
            return [self.oget(k, default, expect) for k in keys]
        elif default:
            return [self.oget(k, default) for k in keys]
        elif expect:
            return [self.oget(k, None, expect) for k in keys]
        return [self.oget(k) for k in keys]

    def omset(self, mapping):
        """Set each key in *mapping* to its corresponding object."""
        # NOTE: Not atomic at the moment
        for key, object in mapping.items():
            self.oset(key, object)

    def __getattr__(self, name):
        # proxy
        return getattr(self.r, name)

class JSONRedisSequence(Generic[T, U], Sequence[T]):
    """Read-Only list interface for JSON objects stored in Redis.

    .. attribute:: r

       Underlying :class:`JSONRedis` client.

    .. attribute:: list_key

       Key of the Redis list that tracks the (keys of the) objects that the sequence contains.

    .. attribute:: pre

       Function of the form *pre()*, which is called before an object is retrieved from the
       database. May be ``None``.
    """

    def __init__(self, r: JSONRedis[U], list_key: str, pre: Callable[[], None] = None,
                 expect: Callable[[U], T] = None) -> None:
        self.r = r
        self.list_key = list_key
        self.pre = pre
        self.expect = expect

    @overload
    def __getitem__(self, key: int) -> T:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    @overload
    def __getitem__(self, key: slice) -> List[T]:
        # pylint: disable=function-redefined,missing-docstring,no-self-use,unused-argument; overload
        pass
    def __getitem__(self, key: Union[int, slice]) -> Union[T, List[T]]:
        # pylint: disable=function-redefined; overload
        if self.pre:
            self.pre()

        if isinstance(key, slice):
            if key.step:
                raise NotImplementedError()
            if key.stop == 0:
                return []
            start = 0 if key.start is None else key.start
            stop = -1 if key.stop is None else key.stop - 1
            ids = [k.decode() for k in cast(List[bytes], self.r.lrange(self.list_key, start, stop))]
            if self.expect:
                return self.r.omget(ids, default=ReferenceError, expect=self.expect)
            return cast(List[T], self.r.omget(ids, default=ReferenceError))

        else:
            id = cast(Optional[bytes], self.r.lindex(self.list_key, key))
            if not id:
                raise IndexError()
            if self.expect:
                return self.r.oget(id.decode(), default=ReferenceError, expect=self.expect)
            return cast(T, self.r.oget(id.decode(), default=ReferenceError))

    def __len__(self):
        return self.r.llen(self.list_key)

class JSONRedisMapping(Generic[T, U], Mapping[str, T]):
    """Simple, read-only map interface for JSON objects stored in Redis.

    Which items the map contains is determined by the Redis list at *map_key*. Because a list is
    used, the map is ordered, i.e. items are retrieved in the order they were inserted.

    .. attribute:: r

       Underlying :class:`JSONRedis` client.

    .. attribute:: map_key

       Key of the Redis list that tracks the (keys of the) objects that the map contains.
    """

    def __init__(self, r: JSONRedis[U], map_key: str,
                 expect: Callable[[Optional[U]], T] = None) -> None:
        self.r = r
        self.map_key = map_key
        self.expect = expect

    def __getitem__(self, key: str) -> T:
        # NOTE: with set:
        #if key not in self:
        if key not in iter(self):
            raise KeyError()
        return (self.r.oget(key, default=ReferenceError, expect=self.expect) if self.expect else
                cast(T, self.r.oget(key, default=ReferenceError)))

    def __iter__(self):
        # NOTE: with set:
        #return (k.decode() for k in self.r.smembers(self.map_key))
        return (k.decode() for k in self.r.lrange(self.map_key, 0, -1))

    def __len__(self):
        # NOTE: with set:
        #return self.r.scard(self.map_key)
        return self.r.llen(self.map_key)

     # NOTE: with set:
     #def __contains__(self, key):
     #    # optimized
     #    return self.r.sismember(self.map_key, key)

    def __repr__(self):
        return str(dict(self))

def expect_type(cls: Type[T]) -> Callable[[object], T]:
    """TODO."""
    def _f(obj: object) -> T:
        if not isinstance(obj, cls):
            raise TypeError()
        return obj
    return _f
