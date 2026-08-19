from pathlib import Path
from typing import Literal

from pydantic import PositiveInt, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE: Path = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "AURA"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: PostgresDsn | None = None
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: PositiveInt = 30

    @field_validator("database_url")
    @classmethod
    def validate_database_driver(
        cls,
        value: PostgresDsn | None,
    ) -> PostgresDsn | None:
        if value is not None and value.scheme != "postgresql+psycopg":
            raise ValueError(
                "DATABASE_URL must use the postgresql+psycopg driver"
            )
        return value

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings: Settings = Settings()
