"""Хранилище сеансов эмуляции: CPU и результат сборки по session id.

Состояние живёт в памяти процесса: перезапуск бэкенда сбрасывает сеансы.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from ..assembler import AssemblyResult
from ..core import Cpu

_SESSION_LIMIT = 1000
_SESSION_TTL_SECONDS = 4 * 60 * 60


@dataclass
class Session:
    id: str
    cpu: Cpu
    assembly: AssemblyResult
    touched_at: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, Session] = {}

    def create(self, cpu: Cpu, assembly: AssemblyResult) -> Session:
        session = Session(uuid.uuid4().hex, cpu, assembly)
        with self._lock:
            self._evict()
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.touched_at = time.monotonic()
            return session

    def _evict(self) -> None:
        now = time.monotonic()
        stale = [key for key, s in self._sessions.items() if now - s.touched_at > _SESSION_TTL_SECONDS]
        for key in stale:
            del self._sessions[key]
        if len(self._sessions) >= _SESSION_LIMIT:
            oldest = min(self._sessions.values(), key=lambda s: s.touched_at)
            del self._sessions[oldest.id]


store = SessionStore()
