from __future__ import annotations

from fastapi import Request

from application.recording_service import RecordingService
from settings import Settings


def get_settings(request: Request) -> Settings:
    """Достаёт настройки, с которыми собрано приложение.

    Args:
        request: Текущий запрос.

    Returns:
        Настройки из `app.state`, их кладёт туда `create_app`.
    """
    settings: Settings = request.app.state.settings
    return settings


def get_recording_service(request: Request) -> RecordingService:
    """Достаёт сервис записей.

    Args:
        request: Текущий запрос.

    Returns:
        Сервис из `app.state`, один на всё приложение.
    """
    service: RecordingService = request.app.state.recording_service
    return service
