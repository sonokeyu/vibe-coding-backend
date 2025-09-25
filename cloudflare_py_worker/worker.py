"""Cloudflare Python Worker (beta) adaptation of the FastAPI endpoints.

Disclaimer:
 1. Python Workers are in beta; APIs / flags may change. Validate with current Cloudflare docs.
 2. Global in‑memory dict `SESSIONS` is NOT durable across isolates / deployments / evictions.
    For production use Durable Objects / KV / D1.
 3. Avoid large third‑party libraries (e.g. full LangChain) due to bundle size & cold start.
 4. This keeps only minimal logic: prompt assembly, OpenRouter call, diff.
"""
import json, uuid, re, difflib
from typing import Any, Dict

# NOTE: Python Worker provides `fetch` / `Response` / `Request` objects from JS via polyglot.
from js import fetch, Response  # type: ignore

SYSTEM_PROMPT = (
    "You are an AI coding assistant that generates or updates a single self-contained web page.\n"
    "Return FULL updated index.html each time inside one fenced code block. Include HTML, minimal CSS, and JavaScript in one file.\n"
    "If user asks for a change, apply it to existing code while preserving prior content unless explicitly removed.\n"
    "Only output the raw code block – no commentary unless user asks for explanation."
)

USER_TEMPLATE = (
    "User request:\n{message}\n\n"
    "Existing code (may be empty):\n```html\n{existing}\n```\n\n"
    "Return ONLY the new full file in a fenced code block."
)

SESSIONS: Dict[str, Dict[str, Any]] = {}


def unified_diff(old: str, new: str, filename: str = "index.html") -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}", lineterm="")
    return "\n".join(diff)


def extract_code_block(text: str) -> str:
    pattern = re.compile(r"```(?:html)?\n(.*?)(?:```)", re.DOTALL)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


async def call_openrouter(env, existing: str, user_message: str) -> tuple[str, str]:
    model = getattr(env, "MODEL", "deepseek/deepseek-chat-v3-0324")
    base_url = getattr(env, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = getattr(env, "OPENROUTER_API_KEY", None)
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    temperature = float(getattr(env, "TEMPERATURE", "0.2"))
    max_tokens = int(getattr(env, "GENERATION_MAX_TOKENS", "2000"))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(message=user_message, existing=existing)},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = await fetch(
        f"{base_url}/chat/completions",
        {
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # OpenRouter optional attribution headers
                "HTTP-Referer": "https://vibe-coding-worker.example",
                "X-Title": "Vibe Coding Python Worker",
            },
            "body": json.dumps(payload),
        },
    )
    if not resp.ok:
        status = resp.status
        txt = await resp.text()
        if status == 403 and ("permission" in txt.lower() or "forbidden" in txt.lower()):
            raise PermissionError("llm_permission_denied")
        raise RuntimeError(f"LLM error {status}: {txt}")

    text_data = await resp.text()
    try:
        data = json.loads(text_data)
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON from LLM")

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    code = extract_code_block(content)
    return content, code


def json_response(obj: Any, status: int = 200, headers: Dict[str, str] | None = None):
    base = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS"}
    if headers:
        base.update(headers)
    return Response.new(json.dumps(obj), {"status": status, "headers": base})


async def handle_request(request, env, ctx):  # noqa: D401
    method = request.method
    url = request.url  # string

    # Preflight CORS
    if method == "OPTIONS":
        return json_response({}, 204)

    # Basic path parse (no query needed here)
    from urllib.parse import urlparse
    path = urlparse(url).path.rstrip("/") or "/"

    if path == "/health":
        return json_response({"status": "ok"})

    if path == "/sessions" and method == "POST":
        sid = str(uuid.uuid4())
        SESSIONS[sid] = {"id": sid, "messages": [], "code": ""}
        return json_response({"session_id": sid})

    # /sessions/{id}/code or /sessions/{id}/messages
    parts = path.split("/")
    if len(parts) >= 3 and parts[1] == "sessions":
        sid = parts[2]
        session = SESSIONS.get(sid)
        if not session:
            return json_response({"detail": "session_not_found"}, 404)
        if len(parts) == 4 and parts[3] == "code" and method == "GET":
            return json_response({"code": session.get("code") or ""})
        if len(parts) == 4 and parts[3] == "messages" and method == "POST":
            body_text = await request.text()
            try:
                payload = json.loads(body_text)
            except Exception:
                return json_response({"detail": "invalid_json"}, 400)
            user_msg = (payload.get("message") or "").strip()
            if not user_msg:
                return json_response({"detail": "empty_message"}, 400)
            previous_code = session.get("code") or ""
            try:
                assistant_text, new_code = await call_openrouter(env, previous_code, user_msg)
            except PermissionError:
                return json_response({"detail": "llm_permission_denied"}, 403)
            except Exception as e:  # other runtime errors
                return json_response({"detail": str(e)}, 500)
            session["messages"].append({"role": "user", "content": user_msg})
            session["messages"].append({"role": "assistant", "content": assistant_text})
            session["code"] = new_code
            diff_txt = unified_diff(previous_code, new_code)
            return json_response({
                "assistant_message": assistant_text,
                "code": new_code,
                "diff": diff_txt,
            })

    return json_response({"detail": "not_found"}, 404)


# Entry point expected by Python Worker runtime (beta names may differ)
async def on_fetch(request, env, ctx):  # noqa: D401
    return await handle_request(request, env, ctx)
