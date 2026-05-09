from app.api.deps import db_enabled
from app.core.config import Settings


def test_db_enabled_true_when_db_url_present() -> None:
    settings = Settings(supabase_db_url='postgresql://postgres:postgres@localhost:5432/postgres')
    assert db_enabled(settings)


def test_db_enabled_false_when_db_url_missing() -> None:
    settings = Settings(supabase_db_url=None)
    assert not db_enabled(settings)
