from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE: Path = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "AURA"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings: Settings = Settings()
