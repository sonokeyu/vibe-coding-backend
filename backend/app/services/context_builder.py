from __future__ import annotations

"""MVP context builder to reduce tokens by truncating large existing code.

Strategy (minimal):
1. If no code or code length <= MAX_CHARS -> return as-is.
2. Else return head portion + tail portion with a marker comment indicating truncation.

Future extensions (not implemented here): structure summary, recent diffs, targeted section extraction.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from app.services.repository import SessionData

MAX_CHARS = 6000  # rough safe size; adjust later
HEAD_KEEP = 3500
TAIL_KEEP = 1800


def build_existing_code_snippet(session: "SessionData", user_message: str) -> str:
    code = session.code or ""
    if len(code) <= MAX_CHARS:
        return code
    head = code[:HEAD_KEEP]
    tail = code[-TAIL_KEEP:]
    omitted = len(code) - (len(head) + len(tail))
    marker = f"\n<!-- TRUNCATED {omitted} chars omitted for context. Model: preserve unchanged middle sections. -->\n"
    return head + marker + tail
