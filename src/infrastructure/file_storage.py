from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from uuid import uuid4

import anyio

from application.dto import RecordingDTO, StoredFileDTO
from domain.recording import (
    RecordingKey,
    is_telemetry_file,
    is_valid_file_name,
    is_valid_segment,
)

READ_CHUNK_BYTES = 64 * 1024
"""Размер куска при отдаче файла клиенту."""

OLDEST = datetime.min.replace(tzinfo=UTC)
"""Ключ сортировки для записи без времени: такие уходят в конец списка."""


class FileRecordingStorage:
    """Записи на локальном диске: `<root>/<device_id>/<recording_id>/<file_name>`.

    Файл сначала пишется во временный `.<имя>.<uuid>.part` в той же папке и
    только потом переименовывается. Оборванная загрузка не оставит половину
    CSV под настоящим именем. Временные файлы в списки не попадают: их имена
    начинаются с точки и не проходят проверку имени.
    """

    def __init__(self, root: Path) -> None:
        """Создаёт хранилище. Папка `root` появится при первой загрузке.

        Args:
            root: Корень, под которым лежат папки телефонов.
        """
        self._root = root

    async def write_file(
        self,
        key: RecordingKey,
        *,
        file_name: str,
        chunks: AsyncIterator[bytes],
    ) -> StoredFileDTO:
        """Записывает файл через временный и заменяет им прежний.

        Args:
            key: Запись, в которую кладётся файл.
            file_name: Имя файла внутри записи.
            chunks: Содержимое кусками.

        Returns:
            Файл в том виде, в каком он лёг на диск.

        Raises:
            Exception: Исключение из `chunks` уходит наружу, временный файл удаляется.
        """
        folder = self._folder(key)
        await anyio.Path(folder).mkdir(parents=True, exist_ok=True)
        target = folder / file_name
        temporary = folder / f".{file_name}.{uuid4().hex}.part"
        try:
            async with await anyio.open_file(temporary, "wb") as output:
                async for chunk in chunks:
                    await output.write(chunk)
            await anyio.Path(temporary).replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return await anyio.to_thread.run_sync(self._describe_file, target)

    async def list_recordings(self, *, device_id: str | None) -> list[RecordingDTO]:
        """Перечисляет записи, у которых есть хотя бы один файл.

        Args:
            device_id: Только записи этого телефона. None — все телефоны.

        Returns:
            Записи от свежих к старым.
        """
        return await anyio.to_thread.run_sync(partial(self._scan, device_id=device_id))

    async def get_recording(self, key: RecordingKey) -> RecordingDTO | None:
        """Читает одну запись.

        Args:
            key: Какая запись нужна.

        Returns:
            Запись с файлами или None, если её папки нет.
        """
        return await anyio.to_thread.run_sync(self._find_recording, key)

    async def stat_file(self, key: RecordingKey, *, file_name: str) -> StoredFileDTO | None:
        """Описывает файл, не читая его.

        Args:
            key: Запись, в которой лежит файл.
            file_name: Имя файла.

        Returns:
            Имя, размер и время изменения или None, если файла нет.
        """
        return await anyio.to_thread.run_sync(self._find_file, self._folder(key) / file_name)

    async def read_file(self, key: RecordingKey, *, file_name: str) -> AsyncIterator[bytes]:
        """Читает файл кусками по `READ_CHUNK_BYTES`.

        Args:
            key: Запись, в которой лежит файл.
            file_name: Имя файла.

        Yields:
            Очередной кусок содержимого.
        """
        async with await anyio.open_file(self._folder(key) / file_name, "rb") as source:
            while chunk := await source.read(READ_CHUNK_BYTES):
                yield chunk

    def _folder(self, key: RecordingKey) -> Path:
        """Строит путь к папке записи.

        Args:
            key: Телефон и запись.

        Returns:
            `<root>/<device_id>/<recording_id>`.
        """
        return self._root / key.device_id / key.recording_id

    def _scan(self, *, device_id: str | None) -> list[RecordingDTO]:
        """Обходит папки телефонов и записей. Блокирующий, вызывается в отдельном потоке.

        Args:
            device_id: Только этот телефон. None — все телефоны.

        Returns:
            Записи с файлами, от свежих к старым.
        """
        if device_id is not None:
            devices = [self._root / device_id]
        elif self._root.is_dir():
            devices = [path for path in self._root.iterdir() if is_valid_segment(path.name)]
        else:
            devices = []
        recordings = [
            self._describe_recording(
                RecordingKey(device_id=device.name, recording_id=folder.name)
            )
            for device in devices
            if device.is_dir()
            for folder in device.iterdir()
            if folder.is_dir() and is_valid_segment(folder.name)
        ]
        return sorted(
            (recording for recording in recordings if recording.files),
            key=lambda recording: recording.updated_at or OLDEST,
            reverse=True,
        )

    def _find_recording(self, key: RecordingKey) -> RecordingDTO | None:
        """Читает запись, если её папка есть. Блокирующий.

        Args:
            key: Телефон и запись.

        Returns:
            Запись с файлами или None.
        """
        if not self._folder(key).is_dir():
            return None
        return self._describe_recording(key)

    def _describe_recording(self, key: RecordingKey) -> RecordingDTO:
        """Собирает запись из файлов её папки. Блокирующий.

        Args:
            key: Телефон и запись. Папка должна существовать.

        Returns:
            Запись с файлами по алфавиту.
        """
        files = sorted(
            (
                self._describe_file(path)
                for path in self._folder(key).iterdir()
                if path.is_file() and is_valid_file_name(path.name) and is_telemetry_file(path.name)
            ),
            key=lambda file: file.file_name,
        )
        return RecordingDTO(
            device_id=key.device_id,
            recording_id=key.recording_id,
            files=files,
            total_bytes=sum(file.size_bytes for file in files),
            updated_at=max((file.modified_at for file in files), default=None),
        )

    def _find_file(self, path: Path) -> StoredFileDTO | None:
        """Описывает файл, если он есть. Блокирующий.

        Args:
            path: Полный путь к файлу.

        Returns:
            Описание файла или None.
        """
        if not path.is_file():
            return None
        return self._describe_file(path)

    @staticmethod
    def _describe_file(path: Path) -> StoredFileDTO:
        """Описывает существующий файл. Блокирующий.

        Args:
            path: Полный путь к файлу.

        Returns:
            Имя, размер и время изменения в UTC.
        """
        stat = path.stat()
        return StoredFileDTO(
            file_name=path.name,
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )
