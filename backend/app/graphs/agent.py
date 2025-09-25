from __future__ import annotations

from app.services.repository import repo, SessionData, CodeVersion
from app.services import llm as llm_service
from app.services import diff as diff_service
from app.services.llm import LLMAccessError
from datetime import datetime


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

    # --- Versioning (MVP) ---
    new_version_number = session.current_version + 1
    version_entry = CodeVersion(
        version=new_version_number,
        code=new_code,
        diff=code_diff,
        summary=None,
        created_at=datetime.utcnow(),
        origin="generation",
    )
    session.versions.append(version_entry)
    session.current_version = new_version_number
    return {
        "assistant_message": assistant_text,
        "assistant_message_raw": assistant_text,
        "code": new_code,
        "diff": code_diff,
        "version": new_version_number,
    }
