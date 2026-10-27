from pathlib import Path

from app.core.config import Settings, get_settings


def test_settings_load_defaults(monkeypatch):
    # Ensure environment variables don't interfere
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings()

    assert settings.app.env == "development"
    assert settings.app.debug is True
    assert settings.database.pool_size == 10

    # Path types
    assert isinstance(settings.dataset.raw_root, Path)
    assert isinstance(settings.ml.model_dir, Path)


def test_settings_override(monkeypatch):
    monkeypatch.setenv("APP__ENV", "production")
    monkeypatch.setenv("DATABASE__POOL_SIZE", "20")

    settings = Settings()
    assert settings.app.env == "production"
    assert settings.database.pool_size == 20


def test_get_settings_is_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_database_url_default(monkeypatch):
    # Ensure DATABASE_URL is not set
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings()
    assert settings.database.url == "postgresql+asyncpg://snakebite:snakebite_dev_password@localhost:5432/snakebite_dev"


def test_database_url_override(monkeypatch):
    test_url = "sqlite+aiosqlite:///./test.db"
    monkeypatch.setenv("DATABASE_URL", test_url)
    settings = Settings()
    assert settings.database.url == test_url
