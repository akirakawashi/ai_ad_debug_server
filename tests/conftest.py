from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import create_app
from settings import Settings

TOKEN = "test-token-0123456789"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(data_dir: Path) -> Iterator[TestClient]:
    settings = Settings(token=TOKEN, data_dir=data_dir, max_file_mb=1)
    with TestClient(create_app(settings)) as test_client:
        yield test_client
