from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
"""Корень репозитория: здесь лежат `.env` и папка `data/` для локального запуска."""

DEFAULT_TOKEN = "local-debug-token"
"""Токен для запуска на своей машине. С ним сервер предупреждает в логе при старте."""


class Settings(BaseSettings):
    """Настройки из переменных окружения и `.env` в корне репозитория.

    Значения по умолчанию подходят для запуска на своей машине. На VPS их
    переопределяет окружение: `docker-compose.yml` читает `.env`, а папку
    данных ставит в `/data` через Dockerfile.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    token: str = Field(
        default=DEFAULT_TOKEN,
        min_length=16,
        validation_alias="DEBUG_SERVER_TOKEN",
        description="Общий токен приложения, приходит в заголовке Authorization: Bearer.",
    )
    data_dir: Path = Field(
        default=PROJECT_ROOT / "data",
        validation_alias="DEBUG_SERVER_DATA_DIR",
        description="Куда складывать записи.",
    )
    max_file_mb: int = Field(
        default=50,
        ge=1,
        le=1024,
        validation_alias="DEBUG_SERVER_MAX_FILE_MB",
        description="Предел размера одного файла в мегабайтах.",
    )

    @property
    def max_file_bytes(self) -> int:
        """Предел размера одного файла.

        Returns:
            `max_file_mb` в байтах.
        """
        return self.max_file_mb * 1024 * 1024

    @property
    def uses_default_token(self) -> bool:
        """Проверяет, запущен ли сервер с токеном по умолчанию.

        Returns:
            True, если `DEBUG_SERVER_TOKEN` не задан.
        """
        return self.token == DEFAULT_TOKEN
