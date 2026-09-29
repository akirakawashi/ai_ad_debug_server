from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

SEGMENT_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
"""Имя устройства или записи: одна папка на диске, до 64 символов.

Первый символ — буква или цифра. Так имя не может быть ни `..`, ни скрытой
папкой, а слэш в шаблон не входит вовсе.
"""

FILE_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
"""Имя файла внутри записи, до 128 символов, по тем же правилам, что и папки."""

TELEMETRY_SUFFIXES: frozenset[str] = frozenset({".csv", ".json"})
"""Что сервер принимает: CSV с координатами, вышками и датчиками и `_meta.json`.

Видео сюда не шлют, его передают отдельно.
"""


@dataclass(frozen=True, slots=True)
class RecordingKey:
    """Адрес записи: папка `<device_id>/<recording_id>`.

    Attributes:
        device_id: Телефон, с которого пришла запись.
        recording_id: Запись на этом телефоне, обычно время старта вида `20260928_195717`.
    """

    device_id: str
    recording_id: str


def is_valid_segment(value: str) -> bool:
    """Проверяет, годится ли строка как имя устройства или записи.

    Args:
        value: Имя из адреса запроса.

    Returns:
        True, если имя подходит под `SEGMENT_PATTERN`.
    """
    return SEGMENT_PATTERN.fullmatch(value) is not None


def is_valid_file_name(value: str) -> bool:
    """Проверяет, годится ли строка как имя файла внутри записи.

    Расширение здесь не проверяется: за него отвечает `is_telemetry_file`.

    Args:
        value: Имя файла из адреса запроса.

    Returns:
        True, если имя подходит под `FILE_NAME_PATTERN`.
    """
    return FILE_NAME_PATTERN.fullmatch(value) is not None


def is_telemetry_file(file_name: str) -> bool:
    """Проверяет, что файл — CSV или JSON, а не видео или что-то ещё.

    Args:
        file_name: Имя файла, уже прошедшее `is_valid_file_name`.

    Returns:
        True, если расширение входит в `TELEMETRY_SUFFIXES`, без учёта регистра.
    """
    return PurePosixPath(file_name).suffix.lower() in TELEMETRY_SUFFIXES
