"""Application configuration and environment validation."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


load_dotenv()


class Settings(BaseModel):
    """Central application settings loaded from environment variables."""

    model_config = ConfigDict(frozen=True)

    mp_ticket: str = Field(default="", alias="MP_TICKET")
    mp_base_url: str = Field(
        default="https://api.mercadopublico.cl/servicios/v1/publico",
        alias="MP_BASE_URL",
    )
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    db_url: str = Field(default="sqlite:///./data/mercado_publico.db", alias="DB_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_backoff_seconds: float = Field(default=1.5, alias="RETRY_BACKOFF_SECONDS")

    @field_validator("mp_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("MP_BASE_URL must start with http:// or https://")
        return value.rstrip("/")

    @field_validator("request_timeout", "max_retries")
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        if value < 1:
            raise ValueError("REQUEST_TIMEOUT and MAX_RETRIES must be greater than 0")
        return value

    @field_validator("retry_backoff_seconds")
    @classmethod
    def validate_backoff(cls, value: float) -> float:
        if value < 0:
            raise ValueError("RETRY_BACKOFF_SECONDS must be greater than or equal to 0")
        return value

    @field_validator("data_dir")
    @classmethod
    def normalize_data_dir(cls, value: Path) -> Path:
        return value.expanduser()

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_data_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def exports_data_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def raw_details_data_dir(self) -> Path:
        return self.raw_data_dir / "details"

    @property
    def logs_data_dir(self) -> Path:
        return self.data_dir / "logs"

    def ensure_directories(self) -> None:
        """Create required data directories if they do not exist."""
        for path in (
            self.data_dir,
            self.raw_data_dir,
            self.raw_details_data_dir,
            self.processed_data_dir,
            self.exports_data_dir,
            self.logs_data_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def _build_settings_payload() -> dict[str, object]:
    return {
        "MP_TICKET": os.getenv("MP_TICKET", ""),
        "MP_BASE_URL": os.getenv("MP_BASE_URL", "https://api.mercadopublico.cl/servicios/v1/publico"),
        "REQUEST_TIMEOUT": os.getenv("REQUEST_TIMEOUT", "30"),
        "DATA_DIR": os.getenv("DATA_DIR", "./data"),
        "DB_URL": os.getenv("DB_URL", "sqlite:///./data/mercado_publico.db"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "MAX_RETRIES": os.getenv("MAX_RETRIES", "3"),
        "RETRY_BACKOFF_SECONDS": os.getenv("RETRY_BACKOFF_SECONDS", "1.5"),
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return validated application settings."""
    try:
        settings = Settings.model_validate(_build_settings_payload())
    except ValidationError as exc:
        raise RuntimeError(f"Invalid environment configuration: {exc}") from exc

    settings.ensure_directories()
    return settings


def require_ticket(settings: Settings | None = None) -> str:
    """Ensure the Mercado Publico ticket is available before API use."""
    active_settings = settings or get_settings()
    if not active_settings.mp_ticket.strip():
        raise RuntimeError(
            "MP_TICKET is empty. Define it in the environment or in the .env file before calling the API."
        )
    return active_settings.mp_ticket.strip()
