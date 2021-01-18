"""CliBroker main module unit tests.
Copyright (c) Kiruse 2021. See license in LICENSE."""
from __future__ import annotations
from asyncio import sleep
from threading import Condition
from typing import *
import asyncio
import clibroker
import io
import pytest

class StringBuffer:
    def __init__(self):
        self.buffer = ''
        self.notif = Condition()
    
    def get(self) -> str:
        return self.buffer
    
    def take(self) -> str:
        buf = self.buffer
        self.buffer = ''
        return buf
    
    def put(self, s: str):
        with self.notif:
            self.buffer += s
            self.notif.notify_all()

class SimStdout(StringBuffer):
    def write(self, msg: str):
        self.put(msg)
    
    def flush(self):
        pass # noop

class SimStdin(StringBuffer):
    def read(self, n: int = -1) -> str:
        with self.notif:
            self.notif.wait_for(lambda: len(self.buffer) > 0)
            ret, self.buffer = self.buffer[:n], self.buffer[n:]
            return ret
    
    def readline(self) -> str:
        with self.notif:
            self.notif.wait_for(lambda: len(self.buffer) > 0)
            try:
                idx = self.buffer.index('\n')
            except ValueError:
                return self.take()
            else:
                ret, self.buffer = self.buffer[:idx+1], self.buffer[idx+1:]
                return ret

class BoolRef:
    def __init__(self, init: bool = False):
        self.value = init
    
    def set(self, value: bool) -> BoolRef:
        self.value = value
        return self
    
    def get(self) -> bool:
        return self.value

buffout = clibroker.clibroker._session.stdout = clibroker.clibroker._session.stderr = SimStdout()
buffin  = clibroker.clibroker._session.stdin  = SimStdin()

def resetbuffs():
    buffout.take()
    buffin.take()

@pytest.mark.asyncio
async def test_write():
    resetbuffs()
    await clibroker.write('test', 1, 2, 3)
    await clibroker.write(',', 123, 456)
    assert buffout.take() == 'test 1 2 3, 123 456'

@pytest.mark.asyncio
async def test_writeline():
    resetbuffs()
    await clibroker.writeline('test', 1, 2, 3)
    await clibroker.writeline(123, 456, 789, sep='_')
    assert buffout.take() == 'test 1 2 3\n123_456_789\n'

@pytest.mark.asyncio
async def test_read():
    resetbuffs()
    
    # Cannot actually simulate "late" input, i.e. two distinct inputs from stdin due to differences in StringIO and sys.stdin.
    buffin.put('test')
    assert await clibroker.read(2) == 'te'
    assert await clibroker.read(2) == 'st'

@pytest.mark.asyncio
async def test_readline():
    resetbuffs()
    
    # Same as with test_read, we cannot properly simulate stdin
    buffin.put('everything')
    assert await clibroker.readline() == 'everything'
    
    buffin.put('test\n123\n456')
    assert await clibroker.readline() == 'test\n'
    assert await clibroker.readline() == '123\n'
    assert buffin.take() == '456'

@pytest.mark.asyncio
async def test_session():
    resetbuffs()
    
    async def without_session():
        await asyncio.sleep(0.1)
        await clibroker.writeline("Without session")
        assert buffout.get() == 'Say something: Without session\n'
    
    async def with_session():
        buffin.put('test123')
        await clibroker.write("Say something: ")
        assert buffout.get() == 'Say something: '
        assert await clibroker.readline() == 'test123'
    
    t1 = asyncio.create_task(without_session())
    t2 = asyncio.create_task(with_session())
    await t1; await t2

@pytest.mark.asyncio
async def test_cancellation():
    t1 = clibroker.readline()
    t2 = clibroker.readline()
    await asyncio.sleep(0.1)
    t1.cancel()
    buffin.put('test')
    assert await asyncio.wait_for(t2, timeout=1) == 'test'

@pytest.mark.asyncio
async def test_standby():
    standby_done = BoolRef(False)
    
    async def task(standby_done: BoolRef):
        assert await clibroker.standby() == 'foobar'
        standby_done.set(True)
    
    t0 = asyncio.create_task(task(standby_done))
    t1 = clibroker.readline()
    t2 = clibroker.readline()
    assert not standby_done.get()
    
    buffin.put('test 1\n')
    buffin.put('test 2')
    assert await t1 == 'test 1\n'
    assert await t2 == 'test 2'
    assert not standby_done.get()
    
    buffin.put('foobar')
    await t0
    assert buffin.take() == ''
    assert standby_done.get()
