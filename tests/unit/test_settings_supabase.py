from app.core.config import Settings


def test_settings_support_supabase_fields() -> None:
    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon",
        supabase_service_role_key="service",
        supabase_db_url="postgresql://postgres:postgres@localhost:5432/postgres",
    )

    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_anon_key == "anon"
    assert settings.supabase_service_role_key == "service"
    assert settings.supabase_db_url.startswith("postgresql://")
