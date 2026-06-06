from __future__ import annotations

import asyncio

import pytest

from paxy.store.models import Entry, Filter
from paxy.store.store import Store


def make_entry(**kwargs) -> Entry:
    defaults = {
        "method": "GET",
        "scheme": "https",
        "host": "example.com",
        "path": "/",
        "protocol": "https",
    }
    defaults.update(kwargs)
    return Entry(**defaults)


def test_add_and_get():
    store = Store()
    e = store.add(make_entry())
    assert e.id == 1
    assert store.get(1) is e
    assert store.get(99) is None


def test_ids_are_sequential():
    store = Store()
    ids = [store.add(make_entry()).id for _ in range(5)]
    assert ids == [1, 2, 3, 4, 5]


def test_list_no_filter():
    store = Store()
    for i in range(3):
        store.add(make_entry(path=f"/{i}"))
    entries, total = store.list(Filter(), 0, 100)
    assert total == 3
    assert len(entries) == 3


def test_list_filter_method():
    store = Store()
    store.add(make_entry(method="GET"))
    store.add(make_entry(method="POST"))
    entries, total = store.list(Filter(method="POST"), 0, 100)
    assert total == 1
    assert entries[0].method == "POST"


def test_list_filter_host():
    store = Store()
    store.add(make_entry(host="a.com"))
    store.add(make_entry(host="b.com"))
    entries, total = store.list(Filter(host="a.com"), 0, 100)
    assert total == 1
    assert entries[0].host == "a.com"


def test_list_filter_search():
    store = Store()
    store.add(make_entry(host="api.example.com", path="/users"))
    store.add(make_entry(host="cdn.example.com", path="/assets"))
    entries, total = store.list(Filter(search="api"), 0, 100)
    assert total == 1
    assert entries[0].host == "api.example.com"


def test_list_pagination():
    store = Store()
    for i in range(10):
        store.add(make_entry(path=f"/{i}"))
    entries, total = store.list(Filter(), offset=3, limit=4)
    assert total == 10
    assert len(entries) == 4


def test_clear():
    store = Store()
    store.add(make_entry())
    store.add(make_entry())
    store.clear()
    _, total = store.list(Filter(), 0, 100)
    assert total == 0


@pytest.mark.asyncio
async def test_subscribe_receives_entry():
    store = Store()
    loop = asyncio.get_event_loop()
    store.set_loop(loop)

    q = store.subscribe()
    e = store.add(make_entry())

    received = await asyncio.wait_for(q.get(), timeout=1.0)
    assert received.id == e.id
    store.unsubscribe(q)


@pytest.mark.asyncio
async def test_unsubscribe_does_not_raise():
    store = Store()
    loop = asyncio.get_event_loop()
    store.set_loop(loop)

    q = store.subscribe()
    store.unsubscribe(q)
    store.unsubscribe(q)  # double unsubscribe should not raise
