from __future__ import annotations

from pydantic import BaseModel


class OkResponse[T](BaseModel):
    """Успешный ответ API: полезные данные всегда лежат в поле `data`.

    Ошибки приходят в другом виде, `{"detail": "<русское предложение>"}`.
    """

    data: T
