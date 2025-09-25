from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class SessionData:
    id: str
    messages: List[ChatMessage] = field(default_factory=list)
    code: Optional[str] = None


class InMemoryRepo:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}

    def create_session(self) -> SessionData:
        sid = str(uuid.uuid4())
        session = SessionData(id=sid)
        self._sessions[sid] = session
        return session

    def get_session(self, session_id: str) -> SessionData:
        if session_id not in self._sessions:
            raise KeyError("session_not_found")
        return self._sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        session = self.get_session(session_id)
        msg = ChatMessage(role=role, content=content)
        session.messages.append(msg)
        return msg

    def update_code(self, session_id: str, code: str) -> None:
        session = self.get_session(session_id)
        session.code = code


repo = InMemoryRepo()
