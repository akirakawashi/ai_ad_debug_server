from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from application.exceptions import (
    FileTooLargeError,
    InvalidNameError,
    RecordingNotFoundError,
    UnsupportedFileError,
)

STATUS_BY_ERROR: dict[type[Exception], int] = {
    InvalidNameError: 400,
    RecordingNotFoundError: 404,
    FileTooLargeError: 413,
    UnsupportedFileError: 415,
}
"""Ошибки приложения и коды ответа. Текст каждой уходит клиенту дословно."""


async def application_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Превращает ошибку приложения в ответ `{"detail": ...}`.

    Код ищется по цепочке наследования: подкласс уже названной ошибки получит
    её код, а не 500.

    Args:
        _: Запрос, на котором случилась ошибка. Не используется.
        exc: Ошибка из `STATUS_BY_ERROR` или её подкласс.

    Returns:
        JSON с кодом из таблицы и текстом ошибки.
    """
    status_code = next(
        STATUS_BY_ERROR[base] for base in type(exc).__mro__ if base in STATUS_BY_ERROR
    )
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


def setup_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчик для каждой ошибки из `STATUS_BY_ERROR`.

    Args:
        app: Приложение, которому нужны обработчики.
    """
    for error_type in STATUS_BY_ERROR:
        app.add_exception_handler(error_type, application_error_handler)
