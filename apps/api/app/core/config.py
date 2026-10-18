from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env at apps/api/.env regardless of the process working directory
# (config.py lives at apps/api/app/core/config.py, so go up three parents).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "CasAI Provenance Lab API"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    cors_origin: str = "http://localhost:3000"
    max_request_bytes: int = 12_000_000
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
    # Vault(s) queried when a prompt doesn't specify one. Demo scope is crop-only;
    # override with DEFAULT_VAULT in .env once more vaults exist.
    default_vault: str = "crop"
    scientific_tool_timeout_seconds: int = 900
    crispor_command: str = "crispor.py"
    crispor_genome_dir: str = ""
    cas_offinder_command: str = "cas-offinder"
    cas_offinder_device: str = "C"
    crispresso_command: str = "CRISPResso"
    indelphi_python: str = "python"
    indelphi_model_dir: str = ""
    intake_workspace_root: Path = _ENV_FILE.parent / ".casai-workspace"

    @field_validator("cors_origin")
    @classmethod
    def validate_cors_origin(cls, value: str) -> str:
        origin = value.rstrip("/")
        if origin == "*" or not origin.startswith(("http://", "https://")):
            raise ValueError("CORS_ORIGIN must be one explicit HTTP(S) origin")
        if "," in origin or " " in origin:
            raise ValueError("CORS_ORIGIN must contain exactly one origin")
        return origin

    @field_validator("max_request_bytes")
    @classmethod
    def validate_request_limit(cls, value: int) -> int:
        if not 1_000_000 <= value <= 100_000_000:
            raise ValueError("MAX_REQUEST_BYTES must be between 1 MB and 100 MB")
        return value

    @model_validator(mode="after")
    def validate_production_transport(self) -> Settings:
        if self.environment == "production" and not self.cors_origin.startswith("https://"):
            raise ValueError("Production CORS_ORIGIN must use HTTPS")
        return self

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
