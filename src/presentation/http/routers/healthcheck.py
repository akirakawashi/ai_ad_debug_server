from __future__ import annotations

from fastapi import APIRouter

healthcheck_router = APIRouter(tags=["Служебное"])


@healthcheck_router.get("/healthcheck", summary="Сервер жив")
async def healthcheck() -> dict[str, str]:
    """Отвечает без токена: по нему Docker и человек проверяют, что сервер поднялся.

    Returns:
        `{"status": "ok"}`.
    """
    return {"status": "ok"}
