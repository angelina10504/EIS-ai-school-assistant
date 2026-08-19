"""XYZ AI backend entrypoint."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat, session_routes, voice
from app.config import BASE_DIR, get_settings
from app.db.session import create_all
from app.i18n.languages import LANGUAGES
from app.llm import get_llm
from app.mock_services import analytics_router, attendance_router, audit_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("xyz-ai")


def _export_google_credentials() -> None:
    """Bridge pydantic-settings → os.environ for the Google Cloud SDKs."""
    settings = get_settings()
    creds = settings.google_application_credentials
    if not creds or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return  # already set by the shell, or nothing configured
    path = Path(creds)
    if not path.is_absolute():
        path = BASE_DIR / path
    if path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
        logger.info("GOOGLE_APPLICATION_CREDENTIALS → %s", path)
    else:
        logger.warning("GOOGLE_APPLICATION_CREDENTIALS points to %s but the file does not exist", path)

# Run at import time — before any Google Cloud SDK client is created.
_export_google_credentials()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if not settings.using_postgres:
        create_all()  # SQLite dev mode; on Supabase the schema comes from schema.sql
    logger.info(
        "XYZ AI starting — db=%s llm=%s",
        "postgres" if settings.using_postgres else "sqlite",
        get_llm().name,
    )
    yield


app = FastAPI(
    title="XYZ AI",
    description="Human-like school assistant — chat, voice and avatar, for students, parents, teachers and the principal.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_routes.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(attendance_router.router)
app.include_router(analytics_router.router)
app.include_router(audit_router.router)


@app.exception_handler(Exception)
async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
    """Never leak a stack trace, a DSN or a key in an error body."""
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side."})


@app.get("/health", tags=["meta"])
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "database": "postgres" if settings.using_postgres else "sqlite",
        "llm": get_llm().name,
        "speech": settings.speech_status,
        "languages": list(LANGUAGES),
    }
