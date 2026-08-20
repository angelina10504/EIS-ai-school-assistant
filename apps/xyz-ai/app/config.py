"""Central settings. Every secret lives here and nowhere near the LLM context."""
import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # Speech
    google_application_credentials: str = ""
    # gRPC prefers IPv6 and stalls ~3s per call on networks with a broken IPv6
    # route, sometimes failing outright. REST avoids that and is markedly faster.
    speech_transport: str = "rest"

    # Data
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""
    sqlite_path: str = str(BASE_DIR / "xyz_ai.db")

    # Auth
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    env: str = "development"

    # How many previous turns get loaded into the model's context window.
    history_turns: int = 12

    @property
    def database_url(self) -> str:
        """Supabase Postgres when configured, otherwise a local SQLite file.

        The SQLite fallback exists so the whole assistant — graph, permissions,
        escalation — can be run and tested without any cloud credentials.
        """
        if self.supabase_db_url and "[PROJECT]" not in self.supabase_db_url:
            return self.supabase_db_url
        return f"sqlite:///{self.sqlite_path}"

    @property
    def using_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def credentials_path(self) -> Path | None:
        """Absolute path to the service-account JSON, if one is configured."""
        raw = self.google_application_credentials.strip()
        if not raw:
            return None
        path = Path(raw).expanduser()
        return path if path.is_absolute() else (BASE_DIR / path).resolve()

    @property
    def speech_status(self) -> str:
        path = self.credentials_path
        if path is None:
            if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                return "configured (from the shell environment)"
            return "not configured — GOOGLE_APPLICATION_CREDENTIALS is unset"
        if not path.exists():
            return f"misconfigured — no file at {path}"
        return f"configured ({path.name})"


def _export_google_credentials(settings: Settings) -> None:
    """Google's client libraries authenticate from os.environ, not from this object.

    pydantic-settings reads .env into the Settings model only, so without this the
    service-account path is loaded and then silently ignored by google.auth.
    """
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return  # a real shell export always wins
    path = settings.credentials_path
    if path is None:
        return
    if not path.exists():
        logger.warning(
            "GOOGLE_APPLICATION_CREDENTIALS points at %s, which does not exist — "
            "voice endpoints will return 503.",
            path,
        )
        return
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
    logger.info("Google Cloud credentials: %s", path)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _export_google_credentials(settings)
    return settings
