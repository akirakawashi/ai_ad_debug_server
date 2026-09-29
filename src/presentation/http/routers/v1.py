from __future__ import annotations

from fastapi import APIRouter

from presentation.http.routers.recordings import recordings_router

API_V1_PREFIX = "/api/v1"
"""Префикс всех маршрутов API, кроме `/healthcheck`."""

api_v1_router = APIRouter()
api_v1_router.include_router(recordings_router)
