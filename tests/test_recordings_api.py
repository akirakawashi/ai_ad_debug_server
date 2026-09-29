from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

DEVICE = "realme-RMX2063"
RECORDING = "20260928_195717"
CELLS = f"{RECORDING}_cells.csv"
CELLS_URL = f"/api/v1/recordings/{DEVICE}/{RECORDING}/files/{CELLS}"
CSV = b"video_ms,type,registered\n588,lte,1\n"


def upload(
    client: TestClient,
    auth: dict[str, str],
    *,
    url: str = CELLS_URL,
    content: bytes = CSV,
) -> dict[str, Any]:
    response = client.put(url, content=content, headers=auth)
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


def test_healthcheck_needs_no_token(client: TestClient) -> None:
    response = client.get("/healthcheck")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong-token-0000000000"},
        {"Authorization": "Basic dXNlcjpwYXNz"},
    ],
)
def test_rejects_missing_or_wrong_token(
    client: TestClient, data_dir: Path, headers: dict[str, str]
) -> None:
    response = client.put(CELLS_URL, content=CSV, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert "Authorization" in response.json()["detail"]
    assert not data_dir.exists()


def test_upload_stores_file_and_reports_hash(
    client: TestClient, auth: dict[str, str], data_dir: Path
) -> None:
    data = upload(client, auth)

    assert data["device_id"] == DEVICE
    assert data["recording_id"] == RECORDING
    assert data["sha256"] == hashlib.sha256(CSV).hexdigest()
    assert data["file"]["file_name"] == CELLS
    assert data["file"]["size_bytes"] == len(CSV)
    assert data["file"]["modified_at"].endswith("Z")
    assert (data_dir / DEVICE / RECORDING / CELLS).read_bytes() == CSV


def test_repeated_upload_replaces_file(
    client: TestClient, auth: dict[str, str], data_dir: Path
) -> None:
    upload(client, auth, content=b"old")
    upload(client, auth, content=CSV)

    folder = data_dir / DEVICE / RECORDING
    assert [path.name for path in folder.iterdir()] == [CELLS]
    assert (folder / CELLS).read_bytes() == CSV


def test_download_returns_stored_bytes(client: TestClient, auth: dict[str, str]) -> None:
    upload(client, auth)

    response = client.get(CELLS_URL, headers=auth)

    assert response.status_code == 200
    assert response.content == CSV
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-length"] == str(len(CSV))
    assert CELLS in response.headers["content-disposition"]


def test_list_recordings_shows_files_and_filters_by_device(
    client: TestClient, auth: dict[str, str]
) -> None:
    upload(client, auth)
    upload(client, auth, url=f"/api/v1/recordings/{DEVICE}/{RECORDING}/files/{RECORDING}.csv")
    upload(client, auth, url=f"/api/v1/recordings/other-phone/{RECORDING}/files/{CELLS}")

    everything = client.get("/api/v1/recordings", headers=auth).json()["data"]
    only_one = client.get(
        "/api/v1/recordings", params={"device_id": DEVICE}, headers=auth
    ).json()["data"]

    assert {recording["device_id"] for recording in everything} == {DEVICE, "other-phone"}
    assert len(only_one) == 1
    assert [file["file_name"] for file in only_one[0]["files"]] == [f"{RECORDING}.csv", CELLS]
    assert only_one[0]["total_bytes"] == 2 * len(CSV)


def test_get_recording_and_unknown_recording(client: TestClient, auth: dict[str, str]) -> None:
    upload(client, auth)

    found = client.get(f"/api/v1/recordings/{DEVICE}/{RECORDING}", headers=auth)
    missing = client.get(f"/api/v1/recordings/{DEVICE}/20000101_000000", headers=auth)

    assert found.status_code == 200
    assert [file["file_name"] for file in found.json()["data"]["files"]] == [CELLS]
    assert missing.status_code == 404
    assert "20000101_000000" in missing.json()["detail"]


def test_download_missing_file(client: TestClient, auth: dict[str, str]) -> None:
    response = client.get(CELLS_URL, headers=auth)

    assert response.status_code == 404
    assert CELLS in response.json()["detail"]


@pytest.mark.parametrize(
    "url",
    [
        f"/api/v1/recordings/.hidden/{RECORDING}/files/{CELLS}",
        f"/api/v1/recordings/{DEVICE}/bad%20name/files/{CELLS}",
        f"/api/v1/recordings/{DEVICE}/{RECORDING}/files/.cells.csv",
        f"/api/v1/recordings/{'x' * 65}/{RECORDING}/files/{CELLS}",
    ],
)
def test_rejects_bad_names(
    client: TestClient, auth: dict[str, str], data_dir: Path, url: str
) -> None:
    response = client.put(url, content=CSV, headers=auth)

    assert response.status_code == 400
    assert "не подходит" in response.json()["detail"]
    assert not data_dir.exists()


def test_rejects_video(client: TestClient, auth: dict[str, str], data_dir: Path) -> None:
    response = client.put(
        f"/api/v1/recordings/{DEVICE}/{RECORDING}/files/{RECORDING}.mp4",
        content=b"\x00\x00\x00\x18ftypmp42",
        headers=auth,
    )

    assert response.status_code == 415
    assert "CSV и JSON" in response.json()["detail"]
    assert not data_dir.exists()


def test_rejects_too_large_file_and_leaves_nothing(
    client: TestClient, auth: dict[str, str], data_dir: Path
) -> None:
    response = client.put(CELLS_URL, content=b"x" * (1024 * 1024 + 1), headers=auth)

    assert response.status_code == 413
    assert "1 МБ" in response.json()["detail"]
    assert list((data_dir / DEVICE / RECORDING).iterdir()) == []
