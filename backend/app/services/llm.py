from __future__ import annotations

"""LLM service layer.

Updated to use the provider-specific LangChain packages (langchain-openai &
langchain-core) instead of the legacy dynamic import path that required
`langchain_community`. This avoids the ModuleNotFoundError the user saw
(`No module named 'langchain_community'`) on LangChain >=0.2.x.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .repository import SessionData
from app.core.config import get_settings
from app.core import prompts
from typing import Iterable, Optional


class LLMAccessError(Exception):
    """Raised when all model attempts fail due to permission/region issues."""

    def __init__(self, attempted: list[str], last_error: Exception):
        super().__init__(f"Permission denied for models: {attempted}. Last error: {last_error}")
        self.attempted = attempted
        self.last_error = last_error


def build_llm(model_name: str) -> ChatOpenAI:
    settings = get_settings()
    # langchain-openai uses `model`, `api_key`, `base_url` parameter names.
    return ChatOpenAI(
        model=model_name,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=settings.temperature,
        max_tokens=settings.generation_max_tokens,
    )


def iter_models() -> Iterable[str]:
    s = get_settings()
    seen = set()
    for m in [s.model, *s.fallback_models]:
        if m and m not in seen:
            seen.add(m)
            yield m


def generate_code(session: SessionData, user_message: str) -> tuple[str, str]:
    """Return (assistant_text, full_code)."""
    existing_code = session.code or ""
    user_content = prompts.USER_INSTRUCTION_TEMPLATE.format(
        message=user_message, existing_code=existing_code
    )
    messages = [
        SystemMessage(content=prompts.SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    attempted: list[str] = []
    last_exc: Optional[Exception] = None
    for model_name in iter_models():
        try:
            attempted.append(model_name)
            llm = build_llm(model_name)
            # Use explicit invoke for clarity with new LangChain API.
            resp = llm.invoke(messages)
            text = resp.content
            code = extract_code_block(text) or text
            return text, code
        except Exception as e:  # Broad catch to handle different openai versions
            if _is_permission_error(e):
                last_exc = e
                continue  # try next fallback
            # Other errors propagate immediately
            raise
    # If we exhausted and only permission errors
    if last_exc:
        raise LLMAccessError(attempted, last_exc)
    raise RuntimeError("No models attempted - configuration error")


def extract_code_block(text: str) -> Optional[str]:
    import re

    pattern = re.compile(r"```(?:html)?\n(.*?)(?:```)", re.DOTALL)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    return None


def _is_permission_error(e: Exception) -> bool:
    name = e.__class__.__name__.lower()
    msg = str(e).lower()
    keywords = ["permission", "forbidden", "unsupported_country", "region", "territory"]
    return any(k in name or k in msg for k in keywords)

