"""Simple manual test to verify proper functioning with std-streams. Complimentary to pytest unit tests.
Copyright (c) Kiruse 2020. See license in LICENSE."""
import asyncio
import clibroker as cli

async def main():
    await cli.writeline('Hello', 'world!', sep=', ')
    t1 = asyncio.create_task(async1())
    t2 = asyncio.create_task(async2())
    await asyncio.wait((t1, t2))

async def async1():
    async with cli.session(autoflush=True) as sess:
        await sess.write("Say something, I'm giving up on you... ")
        response = await sess.readline()
        if len(response) > 0:
            await sess.writeline(f'Too late now. >:c')

async def async2():
    await asyncio.sleep(0.1)
    pw = await cli.password('Secret: ')
    await cli.writeline(f'Your secret is {pw}')

asyncio.run(main())
