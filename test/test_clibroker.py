"""CliBroker main module unit tests.
Copyright (c) Kiruse 2021. See license in LICENSE."""
from asyncio import sleep
from io import StringIO
import asyncio
import clibroker
import io
import pytest

buffout = clibroker.clibroker._session.stdout = clibroker.clibroker._session.stderr = StringIO()
buffin  = clibroker.clibroker._session.stdin  = StringIO()

def takebuff(buff: StringIO):
    buff.seek(0)
    s = buff.read()
    buff.seek(0)
    buff.truncate()
    return s

def pushbuff(buff: StringIO, msg: str):
    buff.seek(0, io.SEEK_END)
    buff.write(msg)
    buff.seek(0)

def resetbuffs():
    takebuff(buffout)
    takebuff(buffin)

@pytest.mark.asyncio
async def test_write():
    resetbuffs()
    await clibroker.write('test', 1, 2, 3)
    await clibroker.write(',', 123, 456)
    assert takebuff(buffout) == 'test 1 2 3, 123 456'

@pytest.mark.asyncio
async def test_writeline():
    resetbuffs()
    await clibroker.writeline('test', 1, 2, 3)
    await clibroker.writeline(123, 456, 789, sep='_')
    assert takebuff(buffout) == 'test 1 2 3\n123_456_789\n'

@pytest.mark.asyncio
async def test_read():
    resetbuffs()
    
    # Cannot actually simulate "late" input, i.e. two distinct inputs from stdin due to differences in StringIO and sys.stdin.
    pushbuff(buffin, 'test')
    assert await clibroker.read(2) == 'te'
    assert await clibroker.read(2) == 'st'

@pytest.mark.asyncio
async def test_readline():
    resetbuffs()
    
    # Same as with test_read, we cannot properly simulate stdin
    pushbuff(buffin, 'everything')
    assert await clibroker.readline() == 'everything'
    takebuff(buffin)
    
    pushbuff(buffin, 'test\n123\n456')
    assert await clibroker.readline() == 'test\n'
    assert await clibroker.readline() == '123\n'
    assert buffin.read() == '456'

@pytest.mark.asyncio
async def test_session():
    resetbuffs()
    
    async def without_session():
        await asyncio.sleep(0.1)
        await clibroker.writeline("Without session")
        assert buffout.getvalue() == 'Say something: Without session\n'
    
    async def with_session():
        pushbuff(buffin, 'test123')
        await clibroker.write("Say something: ")
        assert buffout.getvalue() == 'Say something: '
        assert await clibroker.readline() == 'test123'
    
    t1 = asyncio.create_task(without_session())
    t2 = asyncio.create_task(with_session())
    await t1; await t2

