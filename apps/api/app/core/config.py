from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env at apps/api/.env regardless of the process working directory
# (config.py lives at apps/api/app/core/config.py, so go up three parents).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "CasAI Provenance Lab API"
    api_prefix: str = "/api/v1"
    cors_origin: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_service_key: str = ""
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    # RAG retrieval similarity floor — single source of truth for the default.
    # Measured against the live vault: relevant crop/technique/regulator queries
    # score ~0.55-0.73, off-topic queries top out ~0.17, so 0.25 drops noise
    # without trimming real matches. A tuned starting point; override with
    # RAG_MATCH_THRESHOLD in .env.
    rag_match_threshold: float = 0.25

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
