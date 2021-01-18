# PyCliBroker
Command-line interface I/O broker with sessions for asynchronous applications.

CliBroker provides an asynchronous interface to synchronize stdio read/write commands by FIFO. Sessions allow grouping
such commands together, suspending calls outside of such a session until the active session has terminated. These
sessions can also be nested.

CliBroker processes each request one after another in a single separate thread. CliBroker will properly handle cancellation
of requests.

# Table of Contents
- [PyCliBroker](#pyclibroker)
- [Table of Contents](#table-of-contents)
- [Installation](#installation)
- [Usage](#usage)
  - [Sessions](#sessions)
    - [*async* Session.read(n: int) -> str](#async-sessionreadn-int---str)
    - [*async* Session.readline() -> str](#async-sessionreadline---str)
    - [*async* Session.password(prompt: str = 'Password: ') -> str](#async-sessionpasswordprompt-str--password----str)
    - [*async* Session.write(*data, sep: str = ' ', err: bool = False, flush: Optional[bool] = None)](#async-sessionwritedata-sep-str----err-bool--false-flush-optionalbool--none)
    - [*async* Session.writeline(*data, sep: str = ' ', err: bool = False, flush: Optional[bool] = None)](#async-sessionwritelinedata-sep-str----err-bool--false-flush-optionalbool--none)
    - [*async* Session.flush(flush_stdout: bool = True, flush_stderr: bool = True) -> None](#async-sessionflushflush_stdout-bool--true-flush_stderr-bool--true---none)
    - [*async* Session.standby() -> str](#async-sessionstandby---str)
    - [*async* Session.session(autoflush: Optional[bool] = None) -> Session](#async-sessionsessionautoflush-optionalbool--none---session)
- [Technical Details](#technical-details)
  - [Background Thread](#background-thread)
  - [Global Session](#global-session)
- [Further Testing](#further-testing)
- [License](#license)

# Installation
Simply install via `pip install clibroker`.

# Usage
CliBroker exposes a familiar IO-like interface. A simple example usage is as follows:

```python
import asyncio
import clibroker as cli

async def main():
    cli.writeline('Hello, world!')
    
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


## Sessions
As mentioned above, `clibroker.session` is probably the most useful feature of this library. As the output of the code
above demonstrates, it allows "grouping" CLI commands together and to postpone any other intermittent call until this
session is closed.

CliBroker uses an implicit "global session" to expose specific top-level functions for CLI commands without an associated
session: `read`, `readline`, `write`, `writeline`, `password`, and `session`. Their default behavior in the global
session is documented in their respective sections below.

### *async* Session.read(n: int) -> str
Read at most `n` characters from stdin.

### *async* Session.readline() -> str
Read an entire line from stdin (up until and including the '\n' character).

### *async* Session.password(prompt: str = 'Password: ') -> str
Read a password from stdin similar to Unix-style applications with an optional `prompt`. User input will not be echoed
to stdout.

Caveat: It is possible to rebind output and input streams that a session uses - however `Session.password` will always
use `sys.stdin` and `sys.stdout` (for the prompt). On one hand, this is a limitation of the standard library
[`getpass`](https://docs.python.org/3/library/getpass.html). On the other hand, support for other streams is typically
not needed are likely not mandatorily linked to a console.

### *async* Session.write(*data, sep: str = ' ', err: bool = False, flush: Optional[bool] = None)
Write all `data` stringified and joined by `sep`.

If `err` is false, data is written to stdout, else to stderr.

`flush` dictates whether to immediately flush the output.
* If `flush` is true, output is immediately flushed.
* If `flush` is false, obviously it is not flushed.
* If `flush is None`, resorts to associated session's default autoflush behavior.

Global session's autoflush behavior is true.

### *async* Session.writeline(*data, sep: str = ' ', err: bool = False, flush: Optional[bool] = None)
Same as `Session.write`, except appends a newline character ('\n') to the data.

### *async* Session.flush(flush_stdout: bool = True, flush_stderr: bool = True) -> None
Explicitly flush stdout and/or stderr.

This method is not exposed as top-level function of the global session as the global session always automatically flushes.

### *async* Session.standby() -> str
A special `Session.readline` which lurks to intercept user input while no other read command (`Session.read` or
`Session.readline`) is pending. If a read command is issued or a session opened, standby will be postponed until all
requests are completed first.

### *async* Session.session(autoflush: Optional[bool] = None) -> Session
Creates a new subsession. All subsequent CLI commands on this session will be postponed until this subsession is concluded.

`autoflush` determines the new session's default autoflushing behavior as used by `Session.write` and `Session.writeline`
methods:
* `True`: Automatically flush.
* `False`: Do not automatically flush.
* `None`: Adopt parent session's current autoflush behavior.

The global session by default uses `autoflush=False`.

# Technical Details
**Beware of backpressure!** CliBroker buffers every single request internally in order to achieve predictability.
Backpressure may build up when quickly and regularly queuing requests without ever synchronizing, most noticably with
read requests.

## Background Thread
As mentioned before, CliBroker employs a single background thread to process its queue of requests. In order to avoid
regular termination this background thread is terminated upon completion of all requests. However, as this may lead to
a considerable thread creation overhead, CliBroker waits for new requests for at most 10ms before terminating - a time
span short enough to be barely noticeable but long enough to avoid unnecessary thread creation for most common tasks.

## Global Session
The global session is simply a `Session` whose methods (partly with altered default behavior) are exposed as top-level
bound functions.

The global session can be accessed and changed via `clibroker.clibroker._session` to further alter its default behavior
(such as changing I/O streams). This interface may be useful to the advanced user. It was developed for the purposes of
unit testing and is not intended as part of the public interface.

# Further Testing
CliBroker was developed as part of my hobby project. Currently, I am its sole developer and maintainer. Naturally, I do
not have extensive time to invest into the development of this project. I have set up unit tests for various cases, but
these by far do not provide sufficient coverage.

The following points probably need more testing:

* Multithreaded use - theoretically supported but untested
* Request cancellation
* `standby` feature
* Python version - I'm not entirely sure what the oldest supported Python version is (3.6?)

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

