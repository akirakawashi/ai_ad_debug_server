from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from application.dto import RecordingDTO, StoredFileDTO
from domain.recording import RecordingKey


class RecordingStorage(Protocol):
    """Хранилище записей. Имена сюда приходят уже проверенными сервисом."""

    async def write_file(
        self,
        key: RecordingKey,
        *,
        file_name: str,
        chunks: AsyncIterator[bytes],
    ) -> StoredFileDTO:
        """Записывает файл целиком, заменяя прежний с тем же именем.

        Args:
            key: Запись, в которую кладётся файл.
            file_name: Имя файла внутри записи.
            chunks: Содержимое кусками. Исключение из итератора прерывает запись.

        Returns:
            Файл в том виде, в каком он лёг в хранилище.

        Raises:
            Exception: Любое исключение из `chunks` уходит наружу как есть, а
                недописанный файл не остаётся под настоящим именем.
        """
        ...

    async def list_recordings(self, *, device_id: str | None) -> list[RecordingDTO]:
        """Перечисляет записи.

        Args:
            device_id: Только записи этого телефона. None — записи всех телефонов.

        Returns:
            Записи, у которых есть хотя бы один файл, от свежих к старым.
        """
        ...

    async def get_recording(self, key: RecordingKey) -> RecordingDTO | None:
        """Читает одну запись.

        Args:
            key: Какая запись нужна.

        Returns:
            Запись с её файлами или None, если такой нет.
        """
        ...

    async def stat_file(self, key: RecordingKey, *, file_name: str) -> StoredFileDTO | None:
        """Описывает файл, не читая его.

        Args:
            key: Запись, в которой лежит файл.
            file_name: Имя файла.

        Returns:
            Имя, размер и время изменения или None, если файла нет.
        """
        ...

    def read_file(self, key: RecordingKey, *, file_name: str) -> AsyncIterator[bytes]:
        """Читает файл кусками.

        Args:
            key: Запись, в которой лежит файл.
            file_name: Имя файла. Его существование проверяет вызывающий через `stat_file`.

        Returns:
            Асинхронный итератор по содержимому файла.
        """
        ...
