"""CliBroker implementation.
TODO: Terminal size & auto-word-wrap
Copyright (c) Kiruse 2021. See license in LICENSE."""
from __future__ import annotations
from asyncio import Future as AFuture
from concurrent.futures import Future as CFuture
from getpass import getpass
from threading import Condition, Event, RLock, Thread
import threading
from time import sleep
from typing import *
from warnings import warn
from .utils import *
import sys


class InvalidStateError(Exception): pass
class Reschedule(Exception): pass
class SubsessionCloseWarning(Warning): pass


class Session:
    def __init__(self, parent: Optional[Session] = None, autoflush: Optional[bool] = None, stdout: Optional[IO] = None, stderr: Optional[IO] = None, stdin: Optional[IO] = None):
        self.parent = parent
        self.buffer = ''
        self.pending = RequestQueue()
        self.subsession: Optional[Session] = None
        self._thread: Optional[Thread] = None
        self._threadlock = RLock()
        self._finish_event = SyncEvent()
        self._reschedule_standby = Event()
        
        if parent:
            self.autoflush = autoflush if autoflush is not None else parent.autoflush
            self.stdout = stdout if stdout else parent.stdout
            self.stderr = stderr if stderr else parent.stderr
            self.stdin  = stdin  if stdin  else parent.stdin
        else:
            self.autoflush = autoflush if autoflush is not None else False
            self.stdout = stdout if stdout else sys.stdout
            self.stderr = stderr if stderr else sys.stderr
            self.stdin  = stdin  if stdin  else sys.stdin
    
    
    def read(self, n: int = -1) -> AFuture[str]:
        self._reschedule_standby.set()
        if n < 0:
            return self._commit(ReadAllRequest())
        else:
            return self._commit(ReadRequest(n=n))
    
    def readline(self) -> AFuture[str]:
        self._reschedule_standby.set()
        return self._commit(ReadlineRequest())
    
    def password(self, prompt: str = 'Enter password: ') -> AFuture[str]:
        self._reschedule_standby.set()
        return self._commit(PasswordRequest(prompt=prompt))
    
    def write(self, *data, sep: str = ' ', err: bool = False, autoflush: Optional[bool] = None) -> AFuture[int]:
        return self._commit(WriteRequest(msg=buildmsg(data, sep), err=err, autoflush=autoflush if autoflush is not None else self.autoflush))
    
    def writeline(self, *data, sep: str = ' ', err: bool = False, autoflush: Optional[bool] = None) -> AFuture[int]:
        return self._commit(WriteRequest(msg=buildmsg(data, sep) + '\n', err=err, autoflush=autoflush if autoflush is not None else self.autoflush))
    
    def flush(self, flush_stdout: bool = True, flush_stderr: bool = True) -> AFuture[None]:
        return self._commit(FlushRequest(flush_stdout=flush_stdout, flush_stderr=flush_stderr))
    
    def session(self, autoflush: Optional[bool] = None, stdout: Optional[IO] = None, stderr: Optional[IO] = None, stdin: Optional[IO] = None) -> AFuture[Session]:
        self._reschedule_standby.set()
        return self._commit(SessionRequest(Session(parent=self, stdout=stdout, stdin=stdin, stderr=stderr, autoflush=autoflush)))
    
    def standby(self) -> AFuture[str]:
        return self._commit(StandbyRequest())
    
    def _commit(self, req: BaseRequest):
        self.pending.push(req)
        if not self._thread:
            with self._threadlock:
                if not self._thread:
                    self._thread = Thread(target=self._runner)
                    self._thread.start()
        return asyncio.wrap_future(req.cfuture)
    
    
    def _runner(self):
        self._finish_event.clear()
        while self.subsession:
            self.subsession.wait()
        
        req = self.pending.pop()
        while req:
            try:
                req.execute(self)
            except Reschedule:
                self.pending.push(req)
            req = self.pending.pop(wait=0.01)
        
        with self._threadlock:
            self._thread = None
            self._finish_event.set()
    
    def wait(self):
        self._finish_event.wait()
    
    def __await__(self):
        yield from self._finish_event.__await__()
    
    
    def close(self) -> None:
        if self == _session:
            raise InvalidStateError('Cannot close global session')
        self.pending.clear()
        self._finish_event.set()
    
    def isclosed(self) -> bool:
        return self._finish_event.is_set()
    
    def __enter__(self):
        if self == _session:
            raise InvalidStateError('Cannot enter global session')
        if self != self.parent.subsession:
            raise InvalidStateError('Invalid enter on unregistered subsession')
        return self
    
    def __exit__(self, ex_t, ex_v, ex_tb):
        self.close()


class BaseRequest:
    def __init__(self):
        self.cfuture = CFuture()
    
    def execute(self):
        raise NotImplementedError()

class BaseReadRequest(BaseRequest):
    def execute(self, session: Session):
        if isempty(session.buffer):
            session.buffer += session.stdin.readline()
        
        if not self.cfuture.cancelled():
            try:
                result, session.buffer = self._execute(session)
                self.cfuture.set_result(result)
            except KeyboardInterrupt:
                raise
            except:
                self.cfuture.set_exception(sys.exc_info()[1])
    
    def _execute(self, session: Session) -> Tuple[str, str]:
        raise NotImplementedError()

class ReadRequest(BaseReadRequest):
    def __init__(self, n: int, **kwargs):
        super().__init__(**kwargs)
        assert n >= 0
        self.n = n
    
    def _execute(self, session: Session):
        return session.buffer[:self.n], session.buffer[self.n:]

class ReadAllRequest(BaseReadRequest):
    def _execute(self, session: Session):
        return session.buffer, ''

class ReadlineRequest(BaseReadRequest):
    def _execute(self, session: Session):
        try:
            idx = session.buffer.index('\n')
            return session.buffer[:idx+1], session.buffer[idx+1:]
        except ValueError:
            return session.buffer, ''

class PasswordRequest(BaseRequest):
    def __init__(self, prompt: str, **kwargs):
        super().__init__(**kwargs)
        self.prompt = prompt
    
    def execute(self, session: Session):
        try:
            self.cfuture.set_result(getpass(self.prompt, stream=session.stderr))
        except KeyboardInterrupt:
            raise
        except:
            self.cfuture.set_exception(sys.exc_info()[1])

class WriteRequest(BaseRequest):
    def __init__(self, msg: str, autoflush: bool, err: bool, **kwargs):
        super().__init__(**kwargs)
        self.msg = msg
        self.autoflush = autoflush
        self.err = err
    
    def execute(self, session: Session):
        try:
            io = session.stdout if not self.err else session.stderr
            written = io.write(self.msg)
            if self.autoflush:
                io.flush()
            self.cfuture.set_result(written)
        except KeyboardInterrupt:
            raise
        except:
            self.cfuture.set_exception(sys.exc_info()[1])

class FlushRequest(BaseRequest):
    def __init__(self, flush_stdout = True, flush_stderr = True, **kwargs):
        super().__init__(**kwargs)
        self.flush_stdout = flush_stdout
        self.flush_stderr = flush_stderr
    
    def execute(self, session: Session):
        try:
            session = session.get()
            if self.flush_stdout:
                session.stdout.flush()
            if self.flush_stderr:
                session.stderr.flush()
            self.cfuture.set_result(None)
        except KeyboardInterrupt:
            raise
        except:
            self.cfuture.set_exception(sys.exc_info()[1])

class SessionRequest(BaseRequest):
    def __init__(self, subsession: Session, **kwargs):
        super().__init__(**kwargs)
        self.subsession = subsession
    
    def execute(self, session: Session):
        session.subsession = self.subsession
        self.cfuture.set_result(self.subsession)
        self.subsession.wait() # Postpone this thread's execution until subsession completes.
        session.subsession = None

class StandbyRequest(BaseRequest):
    def execute(self, session: Session):
        if isempty(session.buffer):
            session.buffer += session.stdin.readline()
        
        if session._reschedule_standby.is_set():
            session._reschedule_standby.clear()
            raise Reschedule()
        
        if not self.cfuture.cancelled():
            try:
                idx = session.buffer.index('\n')
            except ValueError:
                ret, session.buffer = session.buffer, ''
                self.cfuture.set_result(ret)
            else:
                ret, session.buffer = session.buffer[:idx+1], session.buffer[idx+1:]
                self.cfuture.set_result(ret)


class RequestQueue:
    def __init__(self):
        self.queue: List[BaseRequest] = []
        self.cond = Condition()
    
    def push(self, req: BaseRequest) -> RequestQueue:
        with self.cond:
            self.queue.append(req)
            self.cond.notify_all()
            return self
    
    def pop(self, wait: Union[int, float, None] = None) -> Optional[BaseRequest]:
        with self.cond:
            self.cond.wait_for(lambda: not isempty(self.queue), wait)
            return shift(self.queue) if not isempty(self.queue) else None
    
    def clear(self) -> RequestQueue:
        with self.cond:
            self.queue = []
            return self

class SyncEvent:
    """A union of `threading.Event` and `asyncio.Event` using `concurrent.futures.Future` and `asyncio.wrap_future`.
    
    Waiting for the event in threadland uses the `wait([timeout])` method while waiting for the event in asyncio-land
    uses `await event`.
    
    Note that the extra overhead of thread synchronization is likely less efficient than a pure `asyncio.Event`. Hence,
    this class should be avoided where possible."""
    
    def __init__(self, initial: bool = False):
        self.lock = Condition()
        self.future = CFuture()
        if initial: self.future.set_result(True)
    
    def clear(self):
        with self.lock:
            self.future = CFuture()
    
    def set(self):
        with self.lock:
            self.future.set_result(True)
            self.lock.notify_all()
    
    def is_set(self) -> bool:
        return self.future.done()
    
    def wait(self, timeout: Optional[float] = None):
        if not self.future.done():
            with self.lock:
                self.lock.wait_for(lambda: self.future.done(), timeout=timeout)
    
    def __await__(self):
        yield from asyncio.wrap_future(self.future).__await__()


def buildmsg(data: Iterable, sep: str) -> str:
    return sep.join(str(dat) for dat in data)


_session = Session(autoflush=True)

read      = _session.read
readline  = _session.readline
write     = _session.write
writeline = _session.writeline
password  = _session.password
standby   = _session.standby

def session(autoflush: bool = False):
    return _session.session(autoflush)

async def wait():
    await _session
