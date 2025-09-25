from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
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
    assistant_message: str  # processed (MVP 等同 raw)
    assistant_message_raw: str
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

# ---- WebSocket streaming (MVP) ----
from app.services import llm as llm_service, diff as diff_service
from app.core import prompts
from langchain_core.messages import SystemMessage, HumanMessage


@router.websocket("/ws/sessions/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        try:
            session = repo.get_session(session_id)
        except KeyError:
            await websocket.send_json({"type": "error", "detail": "session_not_found"})
            await websocket.close(code=4404)
            return

        first = await websocket.receive_json()
        if first.get("type") != "user_message" or "message" not in first:
            await websocket.send_json({"type": "error", "detail": "expected user_message"})
            await websocket.close(code=4400)
            return
        user_message = first["message"]
        repo.add_message(session.id, "user", user_message)
        await websocket.send_json({"type": "ack"})

        existing_code = session.code or ""
        user_content = prompts.USER_INSTRUCTION_TEMPLATE.format(
            message=user_message, existing_code=existing_code
        )
        messages = [
            SystemMessage(content=prompts.SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
        try:
            model_name = next(llm_service.iter_models())
        except StopIteration:
            await websocket.send_json({"type": "error", "detail": "no_model_configured"})
            await websocket.close(code=4500)
            return
        llm = llm_service.build_llm(model_name)
        raw_parts: list[str] = []
        previous_code = session.code or ""
        try:
            async for chunk in llm.astream(messages):  # type: ignore[attr-defined]
                token = chunk.content
                if token:
                    raw_parts.append(token)
                    await websocket.send_json({"type": "token", "text": token})
        except Exception as e:
            await websocket.send_json({"type": "error", "detail": str(e)})
            await websocket.close(code=1011)
            return
        raw_full = "".join(raw_parts)
        code = llm_service.extract_code_block(raw_full) or raw_full
        repo.add_message(session.id, "assistant", raw_full)
        repo.update_code(session.id, code)
        diff_text = diff_service.unified_diff(previous_code, code)
        await websocket.send_json({"type": "assistant_message_complete", "raw": raw_full})
        await websocket.send_json({"type": "code", "code": code})
        await websocket.send_json({"type": "diff", "diff": diff_text})
        await websocket.send_json({"type": "final"})
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
