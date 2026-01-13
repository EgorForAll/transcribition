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

## Тесты

Проект включает комплексные тесты для API эндпоинтов, бизнес-логики и производительности. Тесты написаны с использованием pytest и FastAPI TestClient.

### Запуск тестов
Команды для запуска тестов:
1) `pip install -r requirements-test.txt` - установить зависимости
2) `python -m pytest tests/ -v` - запуск тестов с подробным выводом
 
#### API Endpoints Tests (TestTranscriptionAPI)
1. Корневой эндпоинт
- Проверяет доступность сервиса
- Возвращает информацию о сервисе и доступных эндпоинтах
- тест: **test_root_endpoint()**

2. Транскрибирование аудио в различных форматах
- Поддерживает различные форматы аудио (MP3, WAV, M4A, FLAC)
- Проверяет успешную обработку файлов
- тест: **test_transcribe_valid_audio_formats()**

3. Валидация входных данных 
- Проверка недопустимых расширений файлов
- Проверка отсутствия файла
- тесты: **test_transcribe_invalid_file_extension(), test_transcribe_missing_file()**

4. Скачивание результатов
- Успешное скачивание транскрипции
- Обработка несуществующих транскрипций
- тесты: **test_download_transcription_success(), test_download_nonexistent_transcription()**

5. Обработка больших файлов
- Симуляция работы с большими файлами (10MB+)
- Тест: **test_transcribe_large_file()**

6. Параллельные запросы
- Проверка обработки нескольких одновременных запросов
- тест: **test_concurrent_transcriptions()**


##### Business Logic Tests (TestTranscriptionService)
1. Обработка файлов
- Сохранение загруженных файлов
- Обработка файлов без имени
- тесты: **test_save_upload_file(), test_save_upload_file_no_filename()**

2. Транскрибирование аудио
- Успешное транскрибирование с моком Whisper
- Обработка несуществующих файлов
- тесты: **test_transcribe_audio_success(), test_transcribe_audio_file_not_found()**

3. Сохранение результатов
- Сохранение текста транскрипции в файлы
- тест: **test_save_transcription_text()**

4. Очистка ресурсов
- Удаление временных файлов
- тест: test_cleanup_files()

#### Performance Tests (TestPerformance)
1. Время отклика API
- Измерение времени обработки запросов
- Максимальное время отклика: 10 секунд
- тест: test_response_time()

2. Использование памяти
- Мониторинг утечек памяти при множественных запросах
- Максимальное увеличение памяти: 100MB
- тест: test_memory_usage()