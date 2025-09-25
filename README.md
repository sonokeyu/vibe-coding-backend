# Vibe Coding Backend (MVP)

Minimal FastAPI backend that turns chat instructions into a single-page web prototype (index.html) using an LLM via OpenRouter.

## Features
- Create session
- Send chat message -> generate or update full `index.html`
- Retrieve latest code
- Unified diff between previous and new code

## API
| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /sessions | Create a new session, returns `session_id` |
| POST | /sessions/{session_id}/messages | Send user message, returns assistant message, full code, diff |
| GET | /sessions/{session_id}/code | Get latest code |

### Example Flow
1. Create session: `POST /sessions`
2. Send message: `POST /sessions/{id}/messages` with JSON `{ "message": "Create a landing page with a hero section" }`
3. Inspect returned `code` and `diff`.
4. Iterate with new messages.

## Python Version
Tested with Python 3.9+. Originally written on 3.10; adjusted for 3.9 by:
- Replacing PEP 604 union syntax (`X | Y`) with `typing.Optional` / `typing.Union`.
- No structural pattern matching (`match/case`) used, so no further changes needed.
All listed dependencies declare support for 3.9 (FastAPI, Pydantic v2, Uvicorn, LangChain, LangGraph, OpenAI, httpx).

To create a Python 3.9 virtual environment (macOS):
```bash
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables
See `.env.example`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| OPENROUTER_API_KEY | yes | | Your OpenRouter key |
| MODEL | no | deepseek/deepseek-chat-v3-0324 | Primary model name (default matches code) |
| FALLBACK_MODELS | no | (empty) | Comma-separated fallback model list tried on permission errors |
| OPENROUTER_BASE_URL | no | https://openrouter.ai/api/v1 | Base URL |
| GENERATION_MAX_TOKENS | no | 2000 | Max tokens per completion |
| TEMPERATURE | no | 0.2 | Sampling temperature |

## Run
Install deps and start dev server (note: `--app-dir` should point to the parent directory that contains the `app` package):
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

## Frontend (MVP)
纯静态单文件前端：`frontend/index.html`

启动后端后，直接用浏览器打开该文件（双击或 `open frontend/index.html`）。

功能：
- 左侧：输入指令，显示对话（Agent 回复固定提示）
- 右侧：实时预览最新完整 HTML；展示 unified diff（可滚动）
- 自动创建会话并复用 sessionId；下载按钮可保存当前页面

环境变量 `FALLBACK_MODELS` 可在模型受限时报错时尝试其它模型。


## Tests
```bash
pytest -q  # if import errors, try: PYTHONPATH=backend pytest -q
```

## Notes
MVP: In-memory only; restart loses sessions. Basic permission fallback: if primary model returns region/permission error, iterates FALLBACK_MODELS. 403 with detail `llm_permission_denied` if all fail.
