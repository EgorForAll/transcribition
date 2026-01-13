# Сервис транскрибирования аудио

Легковесный сервис для транскрибирования аудиофайлов в текст с использованием Whisper и FastAPI.

## Возможности

- Загрузка аудиофайлов через HTTP
- Транскрибирование с использованием OpenAI Whisper
- Сохранение результатов в файлы
- Симуляция отправки во внешний API
- REST API интерфейс

## Запуск с Docker

```bash
# Сборка и запуск
docker-compose up --build

# Запуск в фоне
docker-compose up -d

# Остановка
docker-compose down
```

## API Endpoints

### Корневой эндпоинт

`GET /`- Возвращает основную информацию о сервисе и доступные эндпоинты.

Пример ответа (200):

```
{
  "service": "Transcription Service",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "transcribe": "POST /transcribe",
    "download": "GET /transcriptions/{transcription_id}/download",
    "health": "GET /health"
  }
}
```

### Транскрибирование аудио

`POST /transcribe` - загружает аудиофайл для транскрибирования. Сервис обрабатывает аудио с помощью модели Whisper AI и возвращает ID транскрипции для скачивания результата.

##### Заголовки запроса

```text
Content-Type: multipart/form-data
```

#### Параметры формы

| Параметр | Тип    | Обязательный | По умолчанию | Описание                               |
|----------|--------|--------------|--------------|----------------------------------------|
| file     | file   | Да           | -            | Аудиофайл для транскрибирования        |
| language | string | Нет          | ru           | Код языка (например, 'ru', 'en', 'es') |

##### Поддерживаемые форматы аудио

- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- FLAC (.flac)
- OGG (.ogg)
- MP4 (.mp4)
- WEBM (.webm)

#### Поддерживаемые языки

- Русский (ru)
- Английский (en)
- Испанский (es)
- Французский (fr)
- Немецкий (de)

#### Пример с cURL

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "language=ru"
```

#### Успешный ответ
```json
{
  "status": "success",
  "message": "Аудио успешно транскрибировано",
  "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "audio.mp3",
  "text_length": 1250,
  "download_url": "/transcriptions/550e8400-e29b-41d4-a716-446655440000/download",
  "external_api_status": "pending",
  "created_at": "2024-01-12T10:30:00.123456"
}
```

#### Ответы с ошибками

`400 Bad Request` - Неверный формат файла

```json
{
  "error": "HTTP Exception",
  "detail": "Файл должен быть аудиофайлом"
}
```

`500 Internal Server Error` - Ошибка транскрибирования
```json
{
  "error": "HTTP Exception",
  "detail": "Ошибка транскрибирования: [описание ошибки]"
}
```

### Скачивание транскрипции

`GET /transcriptions/{transcription_id}/download` - Скачивает файл с текстом транскрипции. transcription_id получается из ответа эндпоинта /transcribe.

Успешный ответ (200) - Возвращает текстовый файл с содержанием транскрипции.

`404 Not Found` - Файл транскрипции не найден
```json
{
  "error": "HTTP Exception",
  "detail": "Файл транскрипции не найден"
}
```
Пример с cURL:
```bash
curl -X GET "http://localhost:8000/transcriptions/550e8400-e29b-41d4-a716-446655440000/download" \
  -o transcription.txt
```