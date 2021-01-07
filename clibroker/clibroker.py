"""CliBroker implementation.
Copyright (c) Kiruse 2021. See license in LICENSE."""
from __future__ import annotations
from asyncio.exceptions import InvalidStateError
from getpass import getpass
from piodispatch import dispatch
from typing import *
from warnings import warn
from .utils import *
import sys

class SubsessionCloseWarning(Warning):
    pass


class Session:
    def __init__(self, parent: Optional[Session] = None, stdout: IO = sys.stdout, stderr: IO = sys.stderr, stdin: IO = sys.stdin, autoflush: bool = False):
        self.stdout, self.stderr, self.stdin = stdout, stderr, stdin
        self.parent: Optional[Session] = parent
        self.subsession: Optional[Session] = None
        self.autoflush = autoflush
        self._closed = asyncio.Event()
    
    async def read(self, n: int = 1) -> str:
        """Read at most n characters from `stdin`."""
        if self.isclosed():
            raise InvalidStateError("Session closed")
        while self.subsession:
            await self.subsession
        return await dispatch(self.stdin.read, n)
    
    async def readline(self) -> str:
        """Read an entire line from `stdin`."""
        if self.isclosed():
            raise InvalidStateError("Session closed")
        while self.subsession:
            await self.subsession
        return await dispatch(self.stdin.readline)
    
    async def password(self, prompt: str = 'Password: ') -> str:
        """Read a password from `stdin`. The user's input will not be echoed to improve security.
        
        Notice: While it is possible to change CliBroker's stdin, stdout, and stderr streams, `password` only works with
        `sys.stdin` and `sys.stdout`. Other uses are non-sense."""
        if self.isclosed():
            raise InvalidStateError("Session closed")
        while self.subsession:
            await self.subsession
        return await dispatch(getpass, prompt)
    
    async def write(self, *data, sep: str = ' ', err: bool = False, flush: Optional[bool] = None) -> int:
        """Write all `data` stringified and joined by `sep`. If `err` is false, data is written to `stdout`, else to
        `stderr`. If `flush` is true, stream is automatically flushed.
        
        If `flush` is None, resorts to default behavior of the session. Global session has autoflush enabled. By default,
        sessions opened from global session do not autoflush. Other sessions adopt their parent session's autoflush behavior."""
        if self.isclosed():
            raise InvalidStateError("Session closed")
        while self.subsession:
            await self.subsession
        io = self.stdout if not err else self.stderr
        read = await dispatch(io.write, buildmsg(data, sep))
        await self._autoflush(flush, err)
        return read
    
    async def writeline(self, *data, sep: str = ' ', err: bool = False, flush: Optional[bool] = None) -> int:
        """Like `write`, except a newline is appended to the data."""
        if self.isclosed():
            raise InvalidStateError("Session closed")
        while self.subsession:
            await self.subsession
        
        io = self.stdout if not err else self.stderr
        read = await dispatch(io.write, buildmsg(data, sep) + '\n')
        await self._autoflush(flush, err)
        return read
    
    async def _autoflush(self, flush: Optional[bool], err: bool):
        io = self.stdout if not err else self.stderr
        if flush is None:
            flush = self.autoflush
        if flush:
            await dispatch(io.flush)
    
    async def flush(self, flush_stdout: bool = True, flush_stderr: bool = False) -> None:
        """Flush stdout and/or stderr, or neither (for whatever reason)."""
        if self.isclosed():
            raise InvalidStateError("Session closed")
        if flush_stdout:
            await dispatch(self.stdout.flush)
        if flush_stderr:
            await dispatch(self.stderr.flush)
    
    def session(self, autoflush: Optional[bool] = None) -> Session:
        """Create and return a new subsession. Any other command issued on the original session is postponed until the
        subsession is concluded.
        
        The new subsession's autoflush behavior may be specified by these values:
        - `True`: Automatically flush after `write` and `writeline` commands.
        - `False`: Do not automatically flush.
        - `None`: Adopt parent session's autoflush behavior at the time of this call."""
        if self.isclosed():
            raise InvalidStateError("Session closed")
        self.subsession = Session(self, self.stdout, self.stderr, self.stdin, autoflush if autoflush is not None else self.autoflush)
        return self.subsession
    
    
    def close(self):
        """Close this session. The parent's pending commands will be released in order. This session may no longer be
        used to issue commands."""
        self.parent.subsession = None
        if self.subsession:
            warn(SubsessionCloseWarning('An active subsession is being closed'))
            self.subsession.close()
        self._closed.set()
    
    def isclosed(self):
        """Test if this session is already closed."""
        return self._closed.is_set()
    
    async def __aenter__(self):
        if self.isclosed():
            raise InvalidStateError("Session already closed")
        return self
    
    async def __aexit__(self, *args):
        self.close()
    
    def __await__(self):
        yield from self._closed.wait().__await__()


def buildmsg(data: Iterable, sep: str) -> str:
    return sep.join(str(dat) for dat in data)


_session = Session(autoflush=True)

read      = _session.read
readline  = _session.readline
write     = _session.write
writeline = _session.writeline
password  = _session.password

def session(autoflush: bool = False):
    return _session.session(autoflush)
