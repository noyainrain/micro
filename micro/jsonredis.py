# jsonredis
# https://github.com/NoyaInRain/micro/blob/master/jsonredis.py
# part of Micro
# released into the public domain

"""Extended :class:`Redis` client for convinient use with JSON objects.

Also includes :class:`JSONRedisMapping`, an utility map interface for JSON objects.

.. data:: ExpectFunc

   Function of the form `expect(obj: T) -> U` which asserts that an object *obj* is of a certain
   type *U* and raises a :exc:`TypeError` if not.
"""

import json
from typing import (Callable, Dict, Generic, List, Mapping, Optional, Sequence, Type, TypeVar,
                    Union, cast, overload)
from weakref import WeakValueDictionary

from redis import StrictRedis
from redis.exceptions import ResponseError

T = TypeVar('T')
U = TypeVar('U')

ExpectFunc = Callable[[T], U] # pylint: disable=invalid-name; type

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

    @overload
    def oget(self, key: str, *, default: None = None, expect: None = None) -> Optional[T]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def oget(self, key: str, *, default: Union[T, Type[Exception]], expect: None = None) -> T:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def oget(self, key: str, *, default: None = None, expect: ExpectFunc[T, U]) -> Optional[U]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def oget(self, key: str, *, default: Union[T, Type[Exception]], expect: ExpectFunc[T, U]) -> U:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    def oget(self, key: str, default: Union[T, Type[Exception]] = None,
             expect: ExpectFunc[T, U] = None) -> Union[Optional[T], T, U, Optional[U]]:
        """Return the object at *key*.

        If *key* does not exist, *default* is returned. If *default* is an :exc:`Exception`, it is
        raised instead. The object type can be narrowed with *expect*.
        """
        # pylint: disable=function-redefined,missing-docstring; overload
        object = self._cache.get(key) if self.caching else None
        if object is None:
            value = cast(Optional[bytes], self.get(key))
            if value is not None:
                if not value.startswith(b'{'):
                    raise ResponseError()
                try:
                    # loads() actually returns Union[T, Dict[str, object]], but as T may be dict
                    # there is no way to eliminate it here
                    object = cast(T, json.loads(value.decode(), object_hook=self.decode))
                except ValueError:
                    raise ResponseError()
                if self.caching:
                    self._cache[key] = object
        if object is None:
            if isinstance(default, type) and issubclass(default, Exception): # type: ignore
                raise cast(Exception, default(key))
            object = cast(Optional[T], default)
        return expect(object) if expect and object is not None else object

    def oset(self, key: str, object: T) -> None:
        """Set *key* to hold *object*."""
        if self.caching:
            self._cache[key] = object
        self.set(key, json.dumps(object, default=self.encode))

    @overload
    def omget(self, keys: Sequence[str], *, default: None = None,
              expect: None = None) -> List[Optional[T]]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def omget(self, keys: Sequence[str], *, default: Union[T, Type[Exception]],
              expect: None = None) -> List[T]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def omget(self, keys: Sequence[str], *, default: None = None,
              expect: ExpectFunc[T, U]) -> List[Optional[U]]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def omget(self, keys: Sequence[str], *, default: Union[T, Type[Exception]],
              expect: ExpectFunc[T, U]) -> List[U]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    def omget(
            self, keys: Sequence[str], default: Union[T, Type[Exception]] = None,
            expect: ExpectFunc[T, U] = None
        ) -> Union[List[Optional[T]], List[T], List[Optional[U]], List[U]]:
        """Return a list of objects for the given *keys*.

        *default* and *expect* correspond to the arguments of :meth:`oget`."""
        # pylint: disable=function-redefined,missing-docstring; overload
        # NOTE: Not atomic at the moment
        objects = [self.oget(k, default=default, expect=expect) for k in keys]
        return cast(Union[List[Optional[T]], List[T], List[Optional[U]], List[U]], objects)

    def omset(self, mapping):
        """Set each key in *mapping* to its corresponding object."""
        # NOTE: Not atomic at the moment
        for key, object in mapping.items():
            self.oset(key, object)

    def __getattr__(self, name):
        # proxy
        return getattr(self.r, name)

class JSONRedisSequence(Sequence[T]):
    """Read-Only list interface for JSON objects stored in Redis.

    .. attribute:: r

       Underlying :class:`JSONRedis` client.

    .. attribute:: list_key

       Key of the Redis list that tracks the (keys of the) objects that the sequence contains.

    .. attribute:: pre

       Function of the form *pre()*, which is called before an object is retrieved from the
       database. May be ``None``.
    """

    def __init__(self, r: JSONRedis[T], list_key: str, pre: Callable[[], None] = None) -> None:
        self.r = r
        self.list_key = list_key
        self.pre = pre

    def __getitem__(self, key):
        if self.pre:
            self.pre()

        if isinstance(key, slice):
            if key.step:
                raise NotImplementedError()
            if key.stop == 0:
                return []
            start = 0 if key.start is None else key.start
            stop = -1 if key.stop is None else key.stop - 1
            return self.r.omget(k.decode() for k in self.r.lrange(self.list_key, start, stop))

        else:
            id = self.r.lindex(self.list_key, key)
            if not id:
                raise IndexError()
            return self.r.oget(id.decode())

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

    .. attribute:: expect

       Function narrowing the type of retrieved objects. May be ``None``.
    """

    def __init__(self, r: JSONRedis[U], map_key: str, expect: ExpectFunc[U, T] = None) -> None:
        self.r = r
        self.map_key = map_key
        self.expect = expect

    def __getitem__(self, key: str) -> T:
        # NOTE: with set:
        #if key not in self:
        if key not in iter(self):
            raise KeyError()
        return cast(T, self.r.oget(key, default=ReferenceError, expect=self.expect))

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

def expect_type(cls: Type[T]) -> ExpectFunc[object, T]:
    """Return a function which asserts that a given *obj* is an instance of *cls*."""
    def _f(obj: object) -> T:
        if not isinstance(obj, cls):
            raise TypeError()
        return obj
    return _f
