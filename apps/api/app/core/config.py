from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CasAI Provenance Lab API"
    api_prefix: str = "/api/v1"
    cors_origin: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_service_key: str = ""

    model_config = SettingsConfigDict(
        env_file="apps/api/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
