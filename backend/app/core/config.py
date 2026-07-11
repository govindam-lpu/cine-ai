"""Application configuration.

Loaded from environment variables and, for convenience in local dev, a `.env` file.
Follows the pydantic-settings pattern ported from the archive, extended with the writer
backend, Groq, Ollama, and CORS settings the v1 rebuild needs.

Design rule (see docs/00_MASTER_PROMPT.md): the app must boot with no production-only
secrets set. Every optional key defaults to empty and is validated at point of use, never
at import — so local dev (Ollama, no Groq key) starts cleanly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cinerex API"
    app_version: str = "1.0.0"

    # --- Database ---
    # Local: SQLite file. Production: a Turso libSQL URL (sqlite+libsql://...).
    # Database-agnostic ORM keeps these one connection string apart (PLAN.md constraint 6).
    database_url: str = "sqlite:///./cinerex.db"

    # --- TMDB enrichment ---
    # Absent keys degrade gracefully (tmdb client returns empty), never crash at import.
    tmdb_api_key: str = ""
    tmdb_bearer_token: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    # --- Writer backend: prose generation only, never decisions ---
    # "ollama" for local dev, "groq" for production. Chosen at runtime, not import.
    writer_backend: str = "ollama"
    groq_api_key: str = ""                       # production only; unset locally
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b-instruct-q4_K_M"

    # --- CORS ---
    # Comma-separated list of frontend origins allowed to call the API.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        # Runs from backend/; the real secrets live in the repo-root .env one level up.
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
