import re
from datetime import time
from pathlib import Path
from typing import Literal

from pydantic import PositiveInt, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE: Path = Path(__file__).resolve().parents[2] / ".env"
_DAILY_TIME_PATTERN = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


class Settings(BaseSettings):
    app_name: str = "AURA"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: PostgresDsn | None = None
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: PositiveInt = 30
    market_data_update_time_utc: time = time(hour=2)

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

    @field_validator("market_data_update_time_utc", mode="before")
    @classmethod
    def validate_market_data_update_time_utc(cls, value: object) -> time:
        if isinstance(value, time):
            if (
                value.second == 0
                and value.microsecond == 0
                and value.tzinfo is None
            ):
                return value
        elif isinstance(value, str) and _DAILY_TIME_PATTERN.fullmatch(value):
            hour, minute = value.split(":")
            return time(hour=int(hour), minute=int(minute))

        raise ValueError(
            "MARKET_DATA_UPDATE_TIME_UTC must use strict HH:MM format"
        )

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings: Settings = Settings()
