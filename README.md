# ai_ad_debug_server

Временный сборщик для отладки приложения [ai_ad_app](https://github.com/akirakawashi/ai_ad_app).
Телефон после каждой записи шлёт сюда CSV с координатами, вышками и датчиками и `_meta.json`.
Видео сюда не отправляют, его передают отдельно. Базы нет, файлы лежат на диске:
`<папка данных>/<телефон>/<запись>/<файл>`.

## API

Все маршруты, кроме `/healthcheck`, требуют заголовок `Authorization: Bearer <DEBUG_SERVER_TOKEN>`.
Успешный ответ приходит как `{"data": …}`, ошибка — как `{"detail": "…"}`.

| Метод и путь | Что делает |
|---|---|
| `PUT /api/v1/recordings/{телефон}/{запись}/files/{файл}` | Принимает файл сырыми байтами в теле запроса. Только CSV и JSON, до `DEBUG_SERVER_MAX_FILE_MB`. Файл с тем же именем заменяется |
| `GET /api/v1/recordings?device_id=…` | Список записей от свежих к старым, фильтр по телефону необязателен |
| `GET /api/v1/recordings/{телефон}/{запись}` | Одна запись с её файлами |
| `GET /api/v1/recordings/{телефон}/{запись}/files/{файл}` | Скачать файл |
| `GET /healthcheck` | Проверка, что сервер жив. Без токена |

Имена телефона, записи и файла — латиница, цифры, `.`, `_` и `-`, первый символ — буква или цифра.
Интерактивная документация с кнопкой Authorize открывается на `/docs`.

## Настройки

| Переменная | По умолчанию | Что задаёт |
|---|---|---|
| `DEBUG_SERVER_TOKEN` | `local-debug-token` | Токен приложения, не короче 16 символов. Со значением по умолчанию сервер предупреждает в логе |
| `DEBUG_SERVER_DATA_DIR` | `data/` в корне репозитория, в контейнере `/data` | Куда складывать записи |
| `DEBUG_SERVER_MAX_FILE_MB` | `50` | Предел одного файла |
| `DEBUG_SERVER_PORT` | `8000` | Порт на хосте, только для `docker compose` |

Значения берутся из окружения и из `.env` в корне репозитория.

## Запуск у себя

```bash
cd ~/ic8_ai/job_version/ai_ad_debug_server
uv sync
uv run uvicorn main:create_default_app --factory --app-dir src --reload
```

## Запуск на VPS

```bash
git clone https://github.com/akirakawashi/ai_ad_debug_server.git
cd ai_ad_debug_server
cp .env.example .env
sed -i "s/^DEBUG_SERVER_TOKEN=.*/DEBUG_SERVER_TOKEN=$(openssl rand -hex 24)/" .env
docker compose up -d --build
curl http://127.0.0.1:8000/healthcheck
```

Без токена в `.env` контейнер не стартует. Если на VPS включён `ufw`, порт открывают командой
`sudo ufw allow 8000/tcp`. Токен для приложения лежит в `.env`: `grep TOKEN .env`.

Проверить загрузку с компьютера:

```bash
TOKEN=<токен из .env>
curl -X PUT --data-binary @20260928_195717_cells.csv \
  -H "Authorization: Bearer $TOKEN" \
  http://<IP>:8000/api/v1/recordings/test-phone/20260928_195717/files/20260928_195717_cells.csv
curl -H "Authorization: Bearer $TOKEN" http://<IP>:8000/api/v1/recordings
```

Файлы лежат в томе `debug-data`. Забрать их все разом:

```bash
docker compose cp debug-server:/data ./recordings
```

## Проверки

```bash
uv run ruff check . && uv run mypy && uv run pytest
```
