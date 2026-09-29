from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplicationDTO(BaseModel):
    """База DTO слоя приложения: неизменяемые модели, которые без обёрток уходят в ответ API."""

    model_config = ConfigDict(frozen=True)


class StoredFileDTO(ApplicationDTO):
    """Файл, который уже лежит на сервере."""

    file_name: str = Field(description="Имя файла внутри записи.")
    size_bytes: int = Field(ge=0, description="Размер в байтах.")
    modified_at: datetime = Field(description="Когда файл последний раз записали, UTC.")


class RecordingDTO(ApplicationDTO):
    """Запись с одного телефона и всё, что из неё дошло."""

    device_id: str = Field(description="Телефон, с которого пришла запись.")
    recording_id: str = Field(description="Запись на этом телефоне.")
    files: list[StoredFileDTO] = Field(description="Файлы записи по алфавиту.")
    total_bytes: int = Field(ge=0, description="Сумма размеров файлов.")
    updated_at: datetime | None = Field(
        description="Когда пришёл последний файл, UTC. Пусто, если файлов ещё нет."
    )


class UploadedFileDTO(ApplicationDTO):
    """Итог загрузки одного файла."""

    device_id: str = Field(description="Телефон, с которого пришёл файл.")
    recording_id: str = Field(description="Запись, к которой он относится.")
    file: StoredFileDTO = Field(description="Файл в том виде, в каком он лёг на диск.")
    sha256: str = Field(description="SHA-256 принятых байтов, шестнадцатеричной строкой.")


@dataclass(frozen=True, slots=True)
class FileDownload:
    """Файл для отдачи клиенту: описание и поток байтов.

    Не pydantic-модель, потому что держит итератор, а не данные.

    Attributes:
        file: Имя, размер и время изменения файла.
        chunks: Содержимое файла кусками. Читается один раз.
    """

    file: StoredFileDTO
    chunks: AsyncIterator[bytes]
