# ai_ad_debug_server

Временный сервис сбора телеметрии с телефонов во время отладки `ai_ad_app`. После каждой записи телефон отправляет сюда CSV с координатами, вышками, ориентацией и `_meta.json`. Видео сюда не отправляют — оно передаётся отдельно. База данных отсутствует: файлы хранятся на диске в виде `<данные>/<телефон>/<запись>/<файл>`.

Соседний репозиторий: `../ai_ad_app` — Android-приложение, которое шлёт файлы сюда.

---

## Как это работает

Каждая запись — это папка на диске. Имя папки телефона задаёт сам телефон (производитель + модель + часть ANDROID_ID), имя записи — время её старта (`20260928_195717`).

Файл сначала пишется во временный `.<имя>.<uuid>.part` и только потом переименовывается. Прерванная загрузка не оставит неполный CSV под боевым именем. Повторная отправка того же файла безопасна: он просто заменяется.

При каждой загрузке сервер считает SHA-256 принятых байтов и возвращает его в ответе. Телефон сверяет с тем, что посчитал у себя, и при расхождении повторяет отправку.

---

## API

Все маршруты API из таблицы, кроме `/healthcheck`, требуют заголовок
`Authorization: Bearer <DEBUG_SERVER_TOKEN>`. Успешный ответ: `{"data": …}`,
ошибка: `{"detail": "…"}`.

| Метод | Путь | Что делает |
|---|---|---|
| `PUT` | `/api/v1/recordings/{телефон}/{запись}/files/{файл}` | Принимает файл сырыми байтами в теле. Только CSV и JSON, не более `DEBUG_SERVER_MAX_FILE_MB`. Возвращает размер файла и SHA-256 |
| `GET` | `/api/v1/recordings` | Список записей от свежих к старым. `?device_id=…` — только этот телефон |
| `GET` | `/api/v1/recordings/{телефон}/{запись}` | Одна запись: файлы, их размеры и времена изменения |
| `GET` | `/api/v1/recordings/{телефон}/{запись}/files/{файл}` | Скачать файл |
| `GET` | `/healthcheck` | Проверка жизни. Без токена |

**Правила именования.** Имена телефона и записи: до 64 символов. Имена файлов: до 128 символов. Разрешены латиница, цифры, `.`, `_`, `-`; первый символ — буква или цифра. Слеши, пробелы и кириллица не принимаются.

Страницы `/docs`, `/redoc` и схема `/openapi.json` открыты без токена. Кнопка
Authorize в `/docs` добавляет токен только к запросам, которые отправляют со
страницы; саму документацию она не закрывает.

**HTTP-коды ошибок:**

| Код | Причина |
|---|---|
| 400 | Имя телефона, записи или файла не подходит |
| 401 | Токен отсутствует или неверный |
| 404 | Такой записи или файла нет |
| 413 | Файл превышает `DEBUG_SERVER_MAX_FILE_MB` |
| 415 | Файл не CSV и не JSON |
| 500 | Сервер не смог записать файл, например из-за прав на каталог `data/` |

---

## Настройки

Переменные берутся из окружения и из `.env` в корне репозитория.

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DEBUG_SERVER_TOKEN` | `local-debug-token` | Токен из заголовка `Authorization: Bearer`. Не короче 16 символов. Со значением по умолчанию сервер пишет предупреждение в лог при старте |
| `DEBUG_SERVER_DATA_DIR` | `data/` в корне репозитория (в контейнере `/data`) | Куда складываются записи |
| `DEBUG_SERVER_MAX_FILE_MB` | `50` | Предел одного файла, МБ |
| `DEBUG_SERVER_PORT` | `8000` | Порт на хосте — только для `docker compose` |

---

## Запуск у себя

```bash
uv sync
uv run uvicorn main:create_default_app --factory --app-dir src --reload
```

Сервер поднимется на `http://127.0.0.1:8000`.

---

## Запуск на VPS

```bash
git clone https://github.com/akirakawashi/ai_ad_debug_server.git
cd ai_ad_debug_server
cp .env.example .env
sed -i "s/^DEBUG_SERVER_TOKEN=.*/DEBUG_SERVER_TOKEN=$(openssl rand -hex 24)/" .env
mkdir -p data
sudo chown 10001:10001 data
docker compose up -d --build
curl http://127.0.0.1:8000/healthcheck
```

Если пустое значение `DEBUG_SERVER_TOKEN=` в `.env` не заменить, сервер не стартует: pydantic откажет из-за нарушения `min_length=16`.

Контейнер работает под uid 10001 и подключает `./data` с хоста как `/data`.
Права каталога из образа при таком подключении не действуют, поэтому каталог
готовят до запуска контейнера. Если uid 10001 не может писать в него, первая
загрузка завершится ответом 500.

Если включён `ufw`:

```bash
sudo ufw allow 8000/tcp
```

Токен для приложения: `grep TOKEN .env`.

Проверить, что файл отправляется:

```bash
TOKEN=<токен>
curl -X PUT --data-binary @20260928_195717_cells.csv \
  -H "Authorization: Bearer $TOKEN" \
  http://<IP>:8000/api/v1/recordings/test-phone/20260928_195717/files/20260928_195717_cells.csv
curl -H "Authorization: Bearer $TOKEN" http://<IP>:8000/api/v1/recordings
```

Файлы хранятся в папке `data/` в директории репозитория (bind mount `/data` в контейнере):

```bash
cp -r data/ recordings/
```

---

## Структура кода

```
src/
├── main.py                       create_app(settings) для тестов, create_default_app() для uvicorn
├── settings.py                   Settings: токен, папка данных, предел файла
├── domain/recording.py           RecordingKey, проверки имён и типов файлов
├── application/
│   ├── recording_service.py      логика: проверки, SHA-256, вызов хранилища
│   ├── dto.py                    StoredFileDTO, RecordingDTO, UploadedFileDTO
│   ├── interfaces.py             Protocol RecordingStorage
│   └── exceptions.py             InvalidNameError, UnsupportedFileError, FileTooLargeError, …
├── infrastructure/file_storage.py FileRecordingStorage: атомарная запись через .part
└── presentation/http/
    ├── routers/recordings.py     PUT/GET эндпоинты
    ├── security.py               проверка токена через secrets.compare_digest
    ├── responses.py              OkResponse[T]
    └── exception_handlers.py     ошибки приложения → HTTP-коды
```

---

## Проверки

```bash
uv run ruff check . && uv run mypy && uv run pytest
```
