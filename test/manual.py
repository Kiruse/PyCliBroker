"""Simple manual test to verify proper functioning with std-streams. Complimentary to pytest unit tests.
Copyright (c) Kiruse 2020. See license in LICENSE."""
from os import path
import asyncio
import sys

sys.path.append(path.dirname(path.dirname(__file__)))
import clibroker as cli

async def main():
    await cli.writeline('Hello', 'world!', sep=', ')
    t1 = asyncio.create_task(async1())
    t2 = asyncio.create_task(async2())
    await asyncio.wait((t1, t2))

async def async1():
    await asyncio.sleep(0.1)
    pw = await cli.password('Secret: ')
    await cli.writeline(f'Your secret is {pw}')

async def async2():
    with await cli.session(autoflush=True) as sess:
        await sess.write("Hello! Are you there? Say something! ")
        response = await sess.readline()
        if len(response) > 0:
            await sess.writeline(f'Too late now. >:c')

asyncio.run(main())
