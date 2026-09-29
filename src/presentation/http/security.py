from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from presentation.http.dependencies import get_settings
from settings import Settings

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Токен из переменной DEBUG_SERVER_TOKEN.",
)
"""Схема для Swagger: в `/docs` появляется кнопка Authorize для токена."""


def require_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Пропускает запрос только с верным токеном.

    Сравнение идёт через `secrets.compare_digest`, чтобы время ответа не
    подсказывало, сколько символов токена угадано.

    Args:
        credentials: Содержимое заголовка `Authorization: Bearer`, если он есть.
        settings: Настройки с ожидаемым токеном.

    Raises:
        HTTPException: 401, если заголовка нет или токен неверный.
    """
    given = credentials.credentials if credentials is not None else ""
    if not secrets.compare_digest(given.encode(), settings.token.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нужен верный токен в заголовке Authorization: Bearer <токен>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
