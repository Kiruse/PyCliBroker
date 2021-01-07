"""utils.py module unit tests
Copyright (c) Kiruse 2021. See license in LICENSE."""
from clibroker.utils import *
import asyncio


def test_has_running_loop():
    assert not has_running_loop()
    
    asyncio.get_event_loop()
    assert not has_running_loop()
    
    asyncio.get_event_loop().run_until_complete(helper_has_running_loop())
    assert not has_running_loop()

async def helper_has_running_loop():
    assert has_running_loop()


def test_isempty():
    assert isempty(())
    assert isempty([])
    assert isempty({})
    assert isempty(set())
    assert not isempty((1, 2))
    assert not isempty([1, 2])
    assert not isempty({1: 2})
    assert not isempty(set((1, 2)))

def test_shift():
    lst = [1, 2, 3]
    assert shift(lst) == 1
    assert lst == [2, 3]
    assert shift(lst) == 2
    assert lst == [3]
    assert shift(lst) == 3
    assert lst == []

def test_unshift():
    lst = [1]
    unshift(lst, 2)
    assert lst == [2, 1]
    unshift(lst, 3)
    assert lst == [3, 2, 1]
