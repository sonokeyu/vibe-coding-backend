from __future__ import annotations

import os
from typing import Optional
from functools import lru_cache
from pydantic import BaseModel
from dotenv import load_dotenv


load_dotenv()


class Settings(BaseModel):
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    model: str = os.getenv("MODEL", "deepseek/deepseek-chat-v3-0324")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    app_name: str = "Vibe Coding Backend"
    generation_max_tokens: int = int(os.getenv("GENERATION_MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.2"))
    fallback_models: list[str] = [m.strip() for m in os.getenv("FALLBACK_MODELS", "").split(",") if m.strip()]

    class Config:
        arbitrary_types_allowed = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
