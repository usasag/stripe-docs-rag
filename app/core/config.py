from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "stripe-docs-rag"
    app_env: str = "dev"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    model_name: str = "stripe-docs-rag-v1"

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_db_url: str | None = None

    # Crawler settings
    crawler_max_pages: int = 100
    crawler_delay_ms: int = 500

    # LLM synthesis
    litellm_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
