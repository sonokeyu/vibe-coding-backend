from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.api.routes import router as api_router
from pathlib import Path

app = FastAPI(title="Vibe Coding Backend", version="0.1.0")

# Permissive CORS for MVP (front-end opened from file:// or any origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the frontend index.html at root
_INDEX_PATH = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


@app.get("/", response_class=FileResponse)
async def index():
    if not _INDEX_PATH.exists():
        raise HTTPException(status_code=500, detail="index_not_found")
    return FileResponse(str(_INDEX_PATH))


app.include_router(api_router)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

