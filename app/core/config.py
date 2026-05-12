from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "stripe-docs-rag"
    app_env: str = "dev"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    model_name: str = "stripe-docs-rag-v1"

    supabase_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_URL_MASTER", "SUPABASE_URL"),
    )
    supabase_anon_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_ANON_KEY_MASTER", "SUPABASE_ANON_KEY"),
    )
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SUPABASE_SERVICE_ROLE_KEY_MASTER", "SUPABASE_SERVICE_ROLE_KEY"
        ),
    )
    supabase_db_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_DB_URL_MASTER", "SUPABASE_DB_URL"),
    )

    # Crawler settings
    crawler_max_pages: int = 100
    crawler_delay_ms: int = 500

    # LLM synthesis
    llm_provider: str = "github"  # github | anthropic | huggingface
    llm_model: str = "gpt-4o-mini"
    litellm_api_key: str | None = None  # GitHub Models API key
    anthropic_api_key: str | None = None
    hf_api_key: str | None = None  # HuggingFace Inference API key

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
