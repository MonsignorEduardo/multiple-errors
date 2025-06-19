import enum

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.stdlib.get_logger("radar.settings")


class LogLevel(str, enum.Enum):
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    ENVIRONMENT: str = "pytest"
    RELOAD: bool = False
    WORKERS: int = 1
    LOG_LEVEL: LogLevel = LogLevel.INFO
    LOG_JSON_FORMAT: bool = False

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6378

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()  # type: ignore
logger.debug("Settings loaded", settings=settings.model_dump())
