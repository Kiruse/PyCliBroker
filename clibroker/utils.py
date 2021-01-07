"""Simple utility functions extending standard library.
Copyright (c) Kiruse 2021. See license in LICENSE."""
from typing import *
import asyncio

T = TypeVar('T')

def has_running_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False

def isempty(coll: Sequence) -> bool:
    return len(coll) == 0

def shift(lst: List[T]) -> T:
    val = lst[0]
    del lst[0]
    return val

def unshift(lst: List[T], val: T) -> List[T]:
    lst.insert(0, val)
    return lst
    
