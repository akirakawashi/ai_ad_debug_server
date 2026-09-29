from __future__ import annotations


class InvalidNameError(ValueError):
    """Имя устройства, записи или файла не годится как имя на диске."""


class UnsupportedFileError(ValueError):
    """Пришёл не CSV и не JSON. Видео и прочие файлы сервер не принимает."""


class FileTooLargeError(ValueError):
    """Файл больше предела `DEBUG_SERVER_MAX_FILE_MB`."""


class RecordingNotFoundError(LookupError):
    """Нет такой записи или такого файла в ней."""
