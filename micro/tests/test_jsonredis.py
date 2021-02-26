# jsonredis
# Released into the public domain
# https://github.com/noyainrain/micro/blob/master/micro/jsonredis.py

# pylint: disable=missing-docstring; test module

from __future__ import annotations

from collections import OrderedDict
from itertools import count
import json
from threading import Thread
from time import sleep, time
from typing import cast
from unittest import TestCase
from unittest.mock import Mock

from redis import Redis
from redis.exceptions import ResponseError
from typing_extensions import Protocol

from micro.jsonredis import (
    JSONRedis, LexicalRedisSortedSet, RedisList, RedisSequence, RedisSortedSet, JSONRedisSequence,
    JSONRedisMapping, expect_type, bzpoptimed, lexical_value, script, zpoptimed)

class JSONRedisTestCase(TestCase):
    def setUp(self) -> None:
        self.r = JSONRedis(Redis(db=15), encode=Cat.encode, decode=Cat.decode)
        self.r.flushdb()

class JSONRedisTest(JSONRedisTestCase):
    def setup_data(self, cache=True):
        cat = Cat('cat:0', 'Happy')
        if cache:
            self.r.oset(cat.id, cat)
        else:
            self.r.set(cat.id, json.dumps(Cat.encode(cat)))
        return cat

    def test_oset_oget(self):
        cat = self.setup_data()
        got_cat = self.r.oget('cat:0')
        self.assertIsInstance(got_cat, Cat)
        self.assertEqual(got_cat, cat)
        self.assertEqual(got_cat.instance_id, cat.instance_id)

    def test_oset_oget_caching_disabled(self):
        self.r.caching = False

        cat = self.setup_data()
        got_cat = self.r.oget('cat:0')
        self.assertIsInstance(got_cat, Cat)
        self.assertEqual(got_cat, cat)
        self.assertNotEqual(got_cat.instance_id, cat.instance_id)

    def test_oget_object_destroyed(self):
        cat = self.setup_data()
        destroyed_instance_id = cat.instance_id
        del cat
        got_cat = self.r.oget('cat:0')
        self.assertNotEqual(got_cat.instance_id, destroyed_instance_id)

    def test_oget_cache_empty(self):
        self.setup_data(cache=False)

        got_cat = self.r.oget('cat:0')
        same_cat = self.r.oget('cat:0')
        self.assertEqual(same_cat, got_cat)
        self.assertEqual(same_cat.instance_id, got_cat.instance_id)

    def test_oget_cache_empty_caching_disabled(self):
        self.setup_data(cache=False)
        self.r.caching = False

        got_cat = self.r.oget('cat:0')
        same_cat = self.r.oget('cat:0')
        self.assertEqual(same_cat, got_cat)
        self.assertNotEqual(same_cat.instance_id, got_cat.instance_id)

    def test_oget_key_nonexistant(self):
        self.assertIsNone(self.r.oget('foo'))

    def test_oget_value_not_json(self):
        self.r.set('not-json', 'not-json')
        with self.assertRaises(ResponseError):
            self.r.oget('not-json')

    def test_oget_default(self):
        cat = self.setup_data()
        self.assertEqual(self.r.oget(cat.id, default=Cat('cat', 'Default')), cat)

    def test_oget_default_missing_key(self):
        cat = Cat('cat', 'Default')
        self.assertEqual(self.r.oget('foo', default=cat), cat)

    def test_oget_default_exception_missing_key(self):
        with self.assertRaises(KeyError):
            self.r.oget('foo', default=KeyError)

    def test_omget_omset(self):
        cats = {'cat:0': Cat('cat:0', 'Happy'), 'cat:1': Cat('cat:1', 'Grumpy')}
        self.r.omset(cats)
        got_cats = self.r.omget(cats.keys())
        self.assertEqual(got_cats, list(cats.values()))

class TestCaseProtocol(Protocol):
    # pylint: disable=invalid-name; stub
    def setUp(self) -> None: ...
    def assertEqual(self, first: object, second: object) -> None: ...
    def assertTrue(self, expr: object) -> None: ...
    def assertFalse(self, expr: object) -> None: ...

class RedisSequenceTest(TestCaseProtocol):
    seq: RedisSequence

    def setUp(self) -> None:
        self.items = [b'd', b'c', b'b', b'a']

    def test_index(self) -> None:
        self.assertEqual(self.seq.index(b'c'), self.items.index(b'c'))

    def test_index_missing_x(self) -> None:
        with self.assertRaises(ValueError): # type: ignore[misc,attr-defined]
            self.seq.index(b'foo')

    def test_count(self) -> None:
        self.assertEqual(self.seq.count(b'c'), self.items.count(b'c'))

    def test_len(self) -> None:
        self.assertEqual(len(self.seq), len(self.items))

    def test_getitem(self) -> None:
        self.assertEqual(self.seq[1], self.items[1])

    def test_getitem_key_negative(self) -> None:
        self.assertEqual(self.seq[-2], self.items[-2])

    def test_getitem_key_out_of_range(self) -> None:
        with self.assertRaises(IndexError): # type: ignore[misc,attr-defined]
            # pylint: disable=pointless-statement; error is triggered on access
            self.seq[42]

    def test_getitem_key_slice(self) -> None:
        self.assertEqual(self.seq[1:3], self.items[1:3])

    def test_getitem_key_no_start(self) -> None:
        self.assertEqual(self.seq[:3], self.items[:3])

    def test_getitem_key_no_stop(self) -> None:
        self.assertEqual(self.seq[1:], self.items[1:])

    def test_getitem_key_stop_zero(self) -> None:
        self.assertFalse(self.seq[0:0])

    def test_getitem_key_stop_lt_start(self) -> None:
        self.assertFalse(self.seq[3:1])

    def test_getitem_key_stop_negative(self) -> None:
        self.assertEqual(self.seq[1:-1], self.items[1:-1])

    def test_getitem_key_stop_out_of_range(self) -> None:
        self.assertEqual(self.seq[0:42], self.items)

    def test_iter(self) -> None:
        self.assertEqual(list(iter(self.seq)), self.items)

    def test_reversed(self) -> None:
        self.assertEqual(list(reversed(self.seq)), list(reversed(self.items)))

    def test_contains(self) -> None:
        self.assertTrue(b'b' in self.seq)

    def test_contains_missing_item(self) -> None:
        self.assertFalse(b'foo' in self.seq)

class RedisListTest(JSONRedisTestCase, RedisSequenceTest):
    def setUp(self) -> None:
        super().setUp()
        RedisSequenceTest.setUp(self)
        self.r.r.rpush('seq', *self.items)
        self.seq = RedisList('seq', self.r.r)

class RedisSortedSetTest(JSONRedisTestCase, RedisSequenceTest):
    def setUp(self) -> None:
        super().setUp()
        RedisSequenceTest.setUp(self)
        self.r.r.zadd('seq', {item: i for i, item in enumerate(self.items)})
        self.seq = RedisSortedSet('seq', self.r.r)

class LexicalRedisSortedSetTest(JSONRedisTestCase, RedisSequenceTest):
    def setUp(self) -> None:
        super().setUp()
        RedisSequenceTest.setUp(self)
        for i, item in enumerate(self.items):
            item_by_i = lexical_value(item, str(i))
            self.r.r.zadd('seq', {item_by_i: 0})
            self.r.r.hset('seq.lexical', item, item_by_i)
        self.seq = LexicalRedisSortedSet('seq', 'seq.lexical', self.r.r)

class JSONRedisSequenceTest(JSONRedisTestCase):
    def setUp(self):
        super().setUp()
        self.list = [Cat('Cat:0', 'Happy'), Cat('Cat:1', 'Grumpy'), Cat('Cat:2', 'Long'),
                     Cat('Cat:3', 'Monorail')]
        self.r.omset({c.id: c for c in self.list})
        self.r.rpush('cats', *(c.id for c in self.list))
        self.cats = JSONRedisSequence(self.r, 'cats')

    def test_getitem(self):
        self.assertEqual(self.cats[1], self.list[1])

    def test_getitem_key_slice(self):
        self.assertEqual(self.cats[1:3], self.list[1:3])

    def test_getitem_pre(self):
        pre = Mock()
        cats = JSONRedisSequence(self.r, 'cats', pre=pre)
        self.assertTrue(cats[0])
        pre.assert_called_once_with()

    def test_len(self):
        self.assertEqual(len(self.cats), len(self.list))

class JSONRedisMappingTest(JSONRedisTestCase):
    def setUp(self):
        super().setUp()
        self.objects = OrderedDict([
            ('cat:0', Cat('cat:0', 'Happy')),
            ('cat:1', Cat('cat:1', 'Grumpy')),
            ('cat:2', Cat('cat:2', 'Long')),
            ('cat:3', Cat('cat:3', 'Monorail')),
            ('cat:4', Cat('cat:4', 'Ceiling'))
        ])
        self.r.omset(self.objects)
        self.r.rpush('cats', *self.objects.keys())
        self.cats = JSONRedisMapping(self.r, 'cats')

    def test_getitem(self):
        self.assertEqual(self.cats['cat:0'], self.objects['cat:0'])

    def test_iter(self):
        # Use list to also compare order
        self.assertEqual(list(iter(self.cats)), list(iter(self.objects)))

    def test_len(self):
        self.assertEqual(len(self.cats), len(self.objects))

    def test_contains(self):
        self.assertTrue('cat:0' in self.cats)
        self.assertFalse('foo' in self.cats)

class ScriptTest(JSONRedisTestCase):
    def test_script(self) -> None:
        f = script(self.r.r, 'return "Meow!"')
        result = cast(bytes, f()).decode()
        self.assertEqual(result, 'Meow!')

    def test_script_cached(self) -> None:
        f_cached = script(self.r.r, 'return "Meow!"')
        f = script(self.r.r, 'return "Meow!"')
        self.assertIs(f, f_cached)

class ZPopTimedTest(JSONRedisTestCase):
    def make_queue(self, t: float) -> list[tuple[bytes, float]]:
        members = [(value, t + 0.25 * i) for i, value in enumerate([b'a', b'b', b'c'])]
        self.r.r.zadd('queue', dict(members))
        return members

    def test_zpoptimed(self) -> None:
        members = self.make_queue(time() - 0.25)
        result = zpoptimed(self.r.r, 'queue')
        queue = self.r.r.zrange('queue', 0, -1, withscores=True)
        self.assertEqual(result, members[0])
        self.assertEqual(queue, members[1:])

    def test_zpoptimed_future_member(self) -> None:
        members = self.make_queue(time() + 0.25)
        result = zpoptimed(self.r.r, 'queue')
        queue = self.r.r.zrange('queue', 0, -1, withscores=True)
        self.assertEqual(result, members[0][1])
        self.assertEqual(queue, members)

    def test_zpoptimed_empty_set(self) -> None:
        result = zpoptimed(self.r.r, 'queue')
        queue = self.r.r.zrange('queue', 0, -1, withscores=True)
        self.assertEqual(result, float('inf'))
        self.assertFalse(queue)

    def test_bzpoptimed(self) -> None:
        members = self.make_queue(time() - 0.25)
        member = bzpoptimed(self.r.r, 'queue')
        self.assertEqual(member, members[0])

    def test_bzpoptimed_future_member(self) -> None:
        members = self.make_queue(time() + 0.25)
        member = bzpoptimed(self.r.r, 'queue')
        self.assertEqual(member, members[0])

    def test_bzpoptimed_empty_set(self) -> None:
        member = bzpoptimed(self.r.r, 'queue', timeout=0.25)
        self.assertIsNone(member)

    def test_bzpoptimed_on_set_update(self) -> None:
        new = (b'x', time() + 0.5)
        def _add() -> None:
            sleep(0.25)
            self.r.r.zadd('queue', {new[0]: new[1]})
        thread = Thread(target=_add)
        thread.start()
        member = bzpoptimed(self.r.r, 'queue')
        thread.join()
        self.assertEqual(member, new)

class LexicalValueTest(TestCase):
    def test_lexical_value(self) -> None:
        value = lexical_value('x', 'aÄ')
        self.assertGreater(value, b'aa\0y')
        self.assertLess(value, b'ab\0z')

class Cat:
    # We use an instance id generator instead of id() because "two objects with non-overlapping
    # lifetimes may have the same id() value"
    instance_ids = count()

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name
        self.instance_id = next(self.instance_ids)

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name

    @staticmethod
    def encode(object: Cat) -> dict[str, object]:
        return {'id': object.id, 'name': object.name}

    @staticmethod
    def decode(json: dict[str, object]) -> Cat:
        # pylint: disable=redefined-outer-name; good name
        return Cat(id=expect_type(str)(json['id']), name=expect_type(str)(json['name']))
