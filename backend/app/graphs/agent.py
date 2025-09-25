from __future__ import annotations

from app.services.repository import repo, SessionData
from app.services import llm as llm_service
from app.services import diff as diff_service
from app.services.llm import LLMAccessError


def run_generation(session: SessionData, user_message: str) -> dict:
    """Generate/update code for a session given a user message.

    Returns dict including assistant_message_raw for front-end toggle.
    MVP: assistant_message == assistant_message_raw.
    """
    previous_code = session.code or ""
    try:
        assistant_text, new_code = llm_service.generate_code(session, user_message)
    except LLMAccessError:
        raise
    repo.add_message(session.id, "user", user_message)
    repo.add_message(session.id, "assistant", assistant_text)
    repo.update_code(session.id, new_code)
    code_diff = diff_service.unified_diff(previous_code, new_code)
    return {
        "assistant_message": assistant_text,
        "assistant_message_raw": assistant_text,
        "code": new_code,
        "diff": code_diff,
    }
