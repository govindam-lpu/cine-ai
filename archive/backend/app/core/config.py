from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cinerex API"
    app_version: str = "1.0.0"
    database_url: str = "sqlite:///./cine_ai.db"
    tmdb_api_key: str = ""
    tmdb_bearer_token: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")


settings = Settings()
