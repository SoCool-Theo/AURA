import re
from datetime import time
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, PositiveInt, PostgresDsn, SecretStr, field_validator
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
    market_data_refresh_max_attempts: Annotated[int, Field(ge=1, le=5)] = 3
    market_data_refresh_retry_seconds: Annotated[int, Field(ge=1, le=60)] = 10
    market_data_worker_database_url: PostgresDsn | None = None
    forecasting_artifact_version: Annotated[
        str, Field(pattern=r"^forecast-v[0-9]+-[0-9]{8}$")
    ] = "forecast-v1-20260917"

    # AI / LLM configuration
    aura_llm_provider: Literal["openai", "groq"] | None = None
    openai_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    aura_llm_model: str | None = None
    aura_llm_timeout_seconds: Annotated[
        float,
        Field(gt=0, le=120),
    ] = 30.0
    aura_llm_max_output_tokens: Annotated[
        int,
        Field(ge=1, le=1500),
    ] = 1200

    # React frontend CORS configuration
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @field_validator("database_url", "market_data_worker_database_url")
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

    @field_validator("aura_llm_model", mode="before")
    @classmethod
    def normalize_aura_llm_model(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("aura_llm_provider", mode="before")
    @classmethod
    def normalize_aura_llm_provider(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().casefold() or None
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not value:
            raise ValueError("CORS_ALLOWED_ORIGINS must not be empty")

        for origin in value:
            parsed = urlsplit(origin)

            try:
                port = parsed.port
            except ValueError as error:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS entries must use valid ports"
                ) from error

            if (
                origin != origin.strip()
                or "*" in origin
                or parsed.scheme not in {"http", "https"}
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or (":" in parsed.netloc and port is None)
            ):
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS entries must be explicit HTTP(S) "
                    "origins without credentials, paths, wildcards, queries, "
                    "or fragments"
                )

        return value

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )


settings: Settings = Settings()
