# AGENTS.md — working context for AI agents

Read this file first. It holds the rules and the map; how to run and call the service is in
[README.md](README.md).

Language note: this file is English on purpose. Docstrings, error messages and the README are
**Russian** — keep writing them that way, following the prose rules in
[`../AGENTS.md`](../AGENTS.md).

## 1. What this is

A temporary collector used while debugging the Android app in `../ai_ad_app`. After each recording
the phone PUTs its telemetry — `<recording>.csv` (GPS and network fixes), `_cells.csv`, `_imu.csv`,
`_gnss.csv` and `_meta.json` — here. **Video is never accepted**; it travels separately. There is no
database: files live on disk as `<DEBUG_SERVER_DATA_DIR>/<device_id>/<recording_id>/<file_name>`.
The production backend is `../ai_ad_backend`; this service must not grow into a copy of it.

## 2. Hard rules

1. **Never commit, never push.** The owner does that. Leave changes in the working tree and say what
   changed.
2. **No comments in code.** What would be a comment goes into a docstring. A tool directive
   (`# type: ignore[code]`, `# noqa`) keeps a short reason on the same line.
3. **Every function, method and class has a Russian docstring in Google style**: a summary, then
   `Args:`, `Returns:` / `Yields:` and `Raises:` wherever they apply. `ruff` (`D`, convention
   `google`) enforces it; only `tests/` is exempt. Docstrings stay true when the code under them
   changes.
4. **The code is in full order after every change:** `ruff check`, `mypy` (strict) and `pytest` are
   clean. Silence a finding only on its own line, with a reason.
5. **Check your own change before reporting it:** re-read the diff, trace callers, walk the edge
   cases (empty body, oversized body, a name with a dot or a slash, a missing file), then run the
   checks. Say what was verified and what was not.
6. **Only CSV and JSON.** `TELEMETRY_SUFFIXES` in `domain/recording.py` is the whole list.

## 3. Layers

`presentation` → `application` → `domain`; `infrastructure` implements `application` interfaces.

| Path | What lives there |
|---|---|
| `src/domain/recording.py` | `RecordingKey` and name/type checks. Pure, imports nothing from the project |
| `src/application/` | `RecordingService`, DTOs (`dto.py`), the `RecordingStorage` protocol (`interfaces.py`), typed errors (`exceptions.py`). Never imports FastAPI |
| `src/infrastructure/file_storage.py` | `FileRecordingStorage`: disk layout, atomic write through a `.part` file |
| `src/presentation/http/` | Routers, bearer-token check, `{"data": …}` envelope, error handlers |
| `src/settings.py` | `Settings`: local defaults, overridden by the environment and `.env` |
| `src/main.py` | `create_app(settings)` for tests, `create_default_app()` for uvicorn `--factory` |
| `tests/` | pytest through FastAPI's `TestClient`, data in `tmp_path` |

## 4. Conventions

* **Named arguments.** Positional only for the one value that names the subject (`key`); the rest are
  keyword-only.
* **Errors** are typed exceptions from `application/exceptions.py` with a Russian sentence; the HTTP
  code comes from `STATUS_BY_ERROR` in `presentation/http/exception_handlers.py`. Services never raise
  `HTTPException`.
* **Config** gets a local default and is read from the environment on top of it.
* **Blocking disk work** runs through `anyio.to_thread` or `anyio.open_file`, never directly in a
  route.

## 5. Commands

```bash
uv sync
uv run uvicorn main:create_default_app --factory --app-dir src --reload
uv run ruff check . && uv run mypy && uv run pytest
docker compose up -d --build
```
