from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.repository import repo
from app.graphs.agent import run_generation
from app.services.llm import LLMAccessError


router = APIRouter()


class CreateSessionResponse(BaseModel):
    session_id: str


class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    assistant_message: str
    code: str
    diff: str


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session():
    session = repo.create_session()
    return CreateSessionResponse(session_id=session.id)


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
def post_message(session_id: str, req: MessageRequest):
    try:
        session = repo.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")
    try:
        result = run_generation(session, req.message)
        return MessageResponse(**result)
    except LLMAccessError as e:
        raise HTTPException(status_code=403, detail="llm_permission_denied") from e


@router.get("/sessions/{session_id}/code")
def get_code(session_id: str):
    try:
        session = repo.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")
    return {"code": session.code or ""}
