from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from application.dto import RecordingDTO, UploadedFileDTO
from application.recording_service import RecordingService
from domain.recording import RecordingKey
from presentation.http.dependencies import get_recording_service
from presentation.http.responses import OkResponse
from presentation.http.security import require_token

MEDIA_TYPES = {
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json",
}
"""Тип содержимого при скачивании, по расширению файла."""

RAW_BODY = {
    "requestBody": {
        "required": True,
        "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
    }
}
"""Описание тела PUT для Swagger: файл уходит сырыми байтами, без multipart."""

Service = Annotated[RecordingService, Depends(get_recording_service)]

recordings_router = APIRouter(
    prefix="/recordings",
    tags=["Записи"],
    dependencies=[Depends(require_token)],
)


@recordings_router.put(
    "/{device_id}/{recording_id}/files/{file_name}",
    summary="Загрузить файл записи",
    description=(
        "Тело запроса — сам файл, сырыми байтами. Принимаются только CSV и JSON. "
        "Файл с тем же именем заменяется, поэтому повторная отправка безопасна."
    ),
    openapi_extra=RAW_BODY,
)
async def upload_file(
    device_id: str,
    recording_id: str,
    file_name: str,
    request: Request,
    service: Service,
) -> OkResponse[UploadedFileDTO]:
    """Принимает файл записи из тела запроса.

    Args:
        device_id: Телефон, с которого пришёл файл.
        recording_id: Запись на этом телефоне.
        file_name: Имя файла внутри записи.
        request: Запрос, тело которого читается потоком.
        service: Сервис записей.

    Returns:
        Что легло на диск и SHA-256 принятых байтов.
    """
    uploaded = await service.upload_file(
        RecordingKey(device_id=device_id, recording_id=recording_id),
        file_name=file_name,
        chunks=request.stream(),
    )
    return OkResponse(data=uploaded)


@recordings_router.get("", summary="Список записей")
async def list_recordings(
    service: Service,
    device_id: Annotated[
        str | None,
        Query(description="Только записи этого телефона."),
    ] = None,
) -> OkResponse[list[RecordingDTO]]:
    """Перечисляет записи, от свежих к старым.

    Args:
        service: Сервис записей.
        device_id: Только записи этого телефона. Без него — все телефоны.

    Returns:
        Записи с их файлами.
    """
    return OkResponse(data=await service.list_recordings(device_id=device_id))


@recordings_router.get("/{device_id}/{recording_id}", summary="Одна запись")
async def get_recording(
    device_id: str,
    recording_id: str,
    service: Service,
) -> OkResponse[RecordingDTO]:
    """Возвращает запись с её файлами.

    Args:
        device_id: Телефон.
        recording_id: Запись на этом телефоне.
        service: Сервис записей.

    Returns:
        Запись с файлами.
    """
    key = RecordingKey(device_id=device_id, recording_id=recording_id)
    return OkResponse(data=await service.get_recording(key))


@recordings_router.get(
    "/{device_id}/{recording_id}/files/{file_name}",
    summary="Скачать файл записи",
    response_class=StreamingResponse,
)
async def download_file(
    device_id: str,
    recording_id: str,
    file_name: str,
    service: Service,
) -> StreamingResponse:
    """Отдаёт файл записи как вложение.

    Args:
        device_id: Телефон.
        recording_id: Запись на этом телефоне.
        file_name: Имя файла.
        service: Сервис записей.

    Returns:
        Поток байтов файла с его размером и типом содержимого.
    """
    download = await service.open_file(
        RecordingKey(device_id=device_id, recording_id=recording_id),
        file_name=file_name,
    )
    suffix = PurePosixPath(file_name).suffix.lower()
    return StreamingResponse(
        download.chunks,
        media_type=MEDIA_TYPES.get(suffix, "application/octet-stream"),
        headers={
            "Content-Length": str(download.file.size_bytes),
            "Content-Disposition": f'attachment; filename="{download.file.file_name}"',
        },
    )
