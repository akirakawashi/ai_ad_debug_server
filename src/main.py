from __future__ import annotations

import logging

from fastapi import FastAPI

from application.recording_service import RecordingService
from infrastructure.file_storage import FileRecordingStorage
from presentation.http.exception_handlers import setup_exception_handlers
from presentation.http.routers.healthcheck import healthcheck_router
from presentation.http.routers.v1 import API_V1_PREFIX, api_v1_router
from settings import Settings

DESCRIPTION = (
    "Временный сборщик для отладки приложения ai_ad_app. Принимает CSV и JSON "
    "с координатами, вышками и датчиками. Видео сюда не отправляют."
)
"""Описание сервиса на странице `/docs`."""


def create_app(settings: Settings) -> FastAPI:
    """Собирает приложение: хранилище, сервис, обработчики ошибок и маршруты.

    Тесты вызывают эту функцию со своими настройками, uvicorn — `create_default_app`.

    Args:
        settings: Токен, папка данных и предел размера файла.

    Returns:
        Готовое приложение FastAPI.
    """
    app = FastAPI(title="AI Ad debug server", description=DESCRIPTION)
    app.state.settings = settings
    app.state.recording_service = RecordingService(
        FileRecordingStorage(settings.data_dir),
        max_file_bytes=settings.max_file_bytes,
    )
    setup_exception_handlers(app)
    app.include_router(healthcheck_router)
    app.include_router(api_v1_router, prefix=API_V1_PREFIX)
    return app


def create_default_app() -> FastAPI:
    """Собирает приложение из окружения и предупреждает о токене по умолчанию.

    Точка входа для `uvicorn main:create_default_app --factory`. Отдельной
    переменной `app` нет, чтобы импорт модуля в тестах не читал окружение.

    Returns:
        Приложение с настройками из переменных окружения и `.env`.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings()
    if settings.uses_default_token:
        logging.getLogger("ai_ad_debug_server").warning(
            "DEBUG_SERVER_TOKEN не задан, сервер принимает токен по умолчанию. "
            "На VPS так запускать нельзя."
        )
    return create_app(settings)
