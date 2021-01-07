# PyCliBroker
Command-line interface I/O broker with sessions for asynchronous applications.

CliBroker uses asyncio to synchronize access to `sys.stdout`, `sys.stderr`, and `sys.stdin`. Its main selling point is
sessions which postpone other CLI commands until the session is closed again. This allows to organize concurrent asyncio
programs, which e.g. use CLI to setup concurrent components or integrations without (visual) interruption from others.

# Installation
Simply install via `pip install clibroker`.

# Usage
CliBroker exposes a familiar IO-like interface. A simple example usage is as follows:

```python
import asyncio
import clibroker as cli

async def main():
    await cli.writeline('Hello, world!')
    
    t1 = asyncio.create_task(async1())
    t2 = asyncio.create_task(async2())
    await t1; await t2
    # > Hello, world!
    # > Say something: <input:"test 123">
    # > Thanks for those 9 characters.
    # > Foo

async def async1():
    await asyncio.sleep(0.1)
    await cli.writeline('Foo')

async def async2():
    async with cli.session(autoflush=True) as sess:
        await sess.write('Say something: ')
        input = await sess.readline()
        if len(input) > 0:
            await sess.writeline(f'Thanks for those {len(input)} characters.')
        else:
            await sess.writeline('Okay, then not.')

if __name__ == '__main__':
    asyncio.run(main())
```

As mentioned above, `clibroker.session` is probably the most useful feature of this library. As the output of the code
above demonstrates, it allows "grouping" CLI commands together and to postpone any other intermittent call until this
session is closed.

# Documentation
Documentation is available at [pyclibroker.readthedocs.io](https://pyclibroker.readthedocs.io/).

# License
MIT License

Copyright (c) 2021 Kiruse

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

