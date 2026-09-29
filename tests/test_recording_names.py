from __future__ import annotations

import pytest

from domain.recording import is_telemetry_file, is_valid_file_name, is_valid_segment


@pytest.mark.parametrize("value", ["a", "phone-1", "20260928_195717", "A.b_c-9", "x" * 64])
def test_valid_segments(value: str) -> None:
    assert is_valid_segment(value)


@pytest.mark.parametrize(
    "value", ["", ".", "..", ".hidden", "-lead", "_lead", "a/b", "a b", "телефон", "x" * 65]
)
def test_invalid_segments(value: str) -> None:
    assert not is_valid_segment(value)


@pytest.mark.parametrize("value", ["a.csv", "20260928_195717_meta.json", "x" * 128])
def test_valid_file_names(value: str) -> None:
    assert is_valid_file_name(value)


@pytest.mark.parametrize("value", ["", ".a.csv", "a/b.csv", "a b.csv", "x" * 129])
def test_invalid_file_names(value: str) -> None:
    assert not is_valid_file_name(value)


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("a.csv", True),
        ("a.JSON", True),
        ("a.mp4", False),
        ("a.csv.part", False),
        ("csv", False),
    ],
)
def test_telemetry_files(file_name: str, expected: bool) -> None:
    assert is_telemetry_file(file_name) is expected
