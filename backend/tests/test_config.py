"""Settings load with correct defaults; absent optional (production-only) keys don't raise."""

from app.core.config import Settings


def test_defaults_load_without_optional_keys():
    # _env_file=None isolates from the repo .env so we assert the code defaults.
    s = Settings(_env_file=None)

    assert s.app_name == "Cinerex API"
    assert s.database_url.startswith("sqlite")
    # Local-dev defaults: Ollama writer, no Groq key required.
    assert s.writer_backend == "ollama"
    assert s.groq_api_key == ""            # production-only secret absent → must not raise
    assert s.ollama_host


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("WRITER_BACKEND", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+libsql://example.turso.io")

    s = Settings(_env_file=None)

    assert s.writer_backend == "groq"
    assert s.groq_api_key == "test-key"
    assert s.database_url == "sqlite+libsql://example.turso.io"


def test_cors_origins_parsed_to_list():
    s = Settings(_env_file=None, cors_origins="http://a.com, http://b.com ,")
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]
