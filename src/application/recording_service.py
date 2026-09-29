from __future__ import annotations

import hashlib
import logging
from collections.abc import AsyncIterator
from typing import Protocol

from application.dto import FileDownload, RecordingDTO, UploadedFileDTO
from application.exceptions import (
    FileTooLargeError,
    InvalidNameError,
    RecordingNotFoundError,
    UnsupportedFileError,
)
from application.interfaces import RecordingStorage
from domain.recording import (
    RecordingKey,
    is_telemetry_file,
    is_valid_file_name,
    is_valid_segment,
)

logger = logging.getLogger("ai_ad_debug_server.recordings")

NAME_RULES = "латиница, цифры, «.», «_» или «-», первый символ — буква или цифра"
"""Хвост сообщения об ошибке имени: человек должен сразу увидеть, что поправить."""


class Digest(Protocol):
    """Хэш, который дополняют по кускам, как объекты `hashlib`."""

    def update(self, data: bytes, /) -> None:
        """Дополняет хэш очередным куском.

        Args:
            data: Очередной кусок байтов.
        """
        ...


class RecordingService:
    """Приём, перечисление и выдача файлов записей.

    Сервис проверяет имена и размер, считает SHA-256 и не знает, где лежат
    байты: это дело `RecordingStorage`.
    """

    def __init__(self, storage: RecordingStorage, *, max_file_bytes: int) -> None:
        """Создаёт сервис.

        Args:
            storage: Куда складывать и откуда читать файлы.
            max_file_bytes: Предел размера одного файла в байтах.
        """
        self._storage = storage
        self._max_file_bytes = max_file_bytes

    async def upload_file(
        self,
        key: RecordingKey,
        *,
        file_name: str,
        chunks: AsyncIterator[bytes],
    ) -> UploadedFileDTO:
        """Принимает файл записи, заменяя прежний с тем же именем.

        Повторная отправка того же файла безопасна: приложение шлёт его заново
        после любой ошибки сети, и на диске остаётся последняя целая копия.

        Args:
            key: Телефон и запись, к которым относится файл.
            file_name: Имя файла, например `20260928_195717_cells.csv`.
            chunks: Тело запроса кусками.

        Returns:
            Что легло на диск и SHA-256 принятых байтов.

        Raises:
            InvalidNameError: Имя устройства, записи или файла не годится.
            UnsupportedFileError: Файл не CSV и не JSON.
            FileTooLargeError: Файл больше предела. На диске он не остаётся.
        """
        self._check_key(key)
        self._check_file_name(file_name)
        digest = hashlib.sha256()
        stored = await self._storage.write_file(
            key,
            file_name=file_name,
            chunks=self._limited(chunks, digest=digest),
        )
        logger.info(
            "Принят файл %s/%s/%s, %d байт",
            key.device_id,
            key.recording_id,
            file_name,
            stored.size_bytes,
        )
        return UploadedFileDTO(
            device_id=key.device_id,
            recording_id=key.recording_id,
            file=stored,
            sha256=digest.hexdigest(),
        )

    async def list_recordings(self, *, device_id: str | None = None) -> list[RecordingDTO]:
        """Перечисляет записи, от свежих к старым.

        Args:
            device_id: Только записи этого телефона. None — все телефоны.

        Returns:
            Записи с их файлами.

        Raises:
            InvalidNameError: Имя устройства не годится.
        """
        if device_id is not None:
            self._check_segment(device_id, subject="устройства")
        return await self._storage.list_recordings(device_id=device_id)

    async def get_recording(self, key: RecordingKey) -> RecordingDTO:
        """Возвращает одну запись с её файлами.

        Args:
            key: Телефон и запись.

        Returns:
            Запись с файлами.

        Raises:
            InvalidNameError: Имя устройства или записи не годится.
            RecordingNotFoundError: Такой записи нет.
        """
        self._check_key(key)
        recording = await self._storage.get_recording(key)
        if recording is None:
            raise RecordingNotFoundError(f"Записи {key.device_id}/{key.recording_id} нет.")
        return recording

    async def open_file(self, key: RecordingKey, *, file_name: str) -> FileDownload:
        """Открывает файл записи для скачивания.

        Args:
            key: Телефон и запись.
            file_name: Имя файла.

        Returns:
            Описание файла и поток его байтов.

        Raises:
            InvalidNameError: Имя устройства, записи или файла не годится.
            UnsupportedFileError: Файл не CSV и не JSON.
            RecordingNotFoundError: Такого файла нет.
        """
        self._check_key(key)
        self._check_file_name(file_name)
        stored = await self._storage.stat_file(key, file_name=file_name)
        if stored is None:
            raise RecordingNotFoundError(
                f"Файла {file_name} в записи {key.device_id}/{key.recording_id} нет."
            )
        return FileDownload(
            file=stored,
            chunks=self._storage.read_file(key, file_name=file_name),
        )

    async def _limited(
        self,
        chunks: AsyncIterator[bytes],
        *,
        digest: Digest,
    ) -> AsyncIterator[bytes]:
        """Пропускает куски дальше, пока файл не превысил предел, и считает хэш.

        Args:
            chunks: Тело запроса кусками.
            digest: Хэш, который дополняется каждым пропущенным куском.

        Yields:
            Те же куски, что пришли.

        Raises:
            FileTooLargeError: Принято больше `max_file_bytes` байтов.
        """
        received = 0
        async for chunk in chunks:
            received += len(chunk)
            if received > self._max_file_bytes:
                limit_mb = self._max_file_bytes // (1024 * 1024)
                raise FileTooLargeError(f"Файл больше {limit_mb} МБ.")
            digest.update(chunk)
            yield chunk

    def _check_key(self, key: RecordingKey) -> None:
        """Проверяет имена устройства и записи.

        Args:
            key: Телефон и запись.

        Raises:
            InvalidNameError: Одно из имён не годится.
        """
        self._check_segment(key.device_id, subject="устройства")
        self._check_segment(key.recording_id, subject="записи")

    @staticmethod
    def _check_segment(value: str, *, subject: str) -> None:
        """Проверяет имя устройства или записи.

        Args:
            value: Проверяемое имя.
            subject: Чьё это имя, в родительном падеже: «устройства» или «записи».

        Raises:
            InvalidNameError: Имя не годится.
        """
        if not is_valid_segment(value):
            raise InvalidNameError(
                f"Имя {subject} «{value}» не подходит: {NAME_RULES}, до 64 символов."
            )

    @staticmethod
    def _check_file_name(file_name: str) -> None:
        """Проверяет имя и тип файла.

        Args:
            file_name: Имя файла.

        Raises:
            InvalidNameError: Имя не годится.
            UnsupportedFileError: Файл не CSV и не JSON.
        """
        if not is_valid_file_name(file_name):
            raise InvalidNameError(
                f"Имя файла «{file_name}» не подходит: {NAME_RULES}, до 128 символов."
            )
        if not is_telemetry_file(file_name):
            raise UnsupportedFileError(
                f"Сервер принимает только CSV и JSON, а пришёл «{file_name}»."
            )
