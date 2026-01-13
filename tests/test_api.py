import pytest
import json
import io
import traceback
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile, HTTPException
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.services import TranscriptionService
from app.models import TranscriptionResponse

# Создаем тестового клиента
client = TestClient(app)

# Тестовые данные
TEST_AUDIO_CONTENT = b"fake audio content"
TEST_TRANSCRIPTION_TEXT = "Это тестовый текст транскрипции на русском языке."
TEST_UUID = "123e4567-e89b-12d3-a456-426614174000"


class TestTranscriptionAPI:
    """Тесты для API эндпоинтов"""

    def test_root_endpoint(self):
        """Тест корневого эндпоинта"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        print(f"Actual service name: {data.get('service')}")
        assert "service" in data
        assert "status" in data
        assert data["status"] == "running"
        assert "transcribe" in data["endpoints"]
        assert "download" in data["endpoints"]
        assert "health" in data["endpoints"]

    @pytest.mark.parametrize("file_extension", [".mp3", ".wav", ".m4a", ".flac"])
    def test_transcribe_valid_audio_formats(self, file_extension, mock_transcription_service):
        """Тест транскрибирования с разными форматами аудио"""
        # Создаем мок файл
        files = {
            "file": (f"test_audio{file_extension}", io.BytesIO(TEST_AUDIO_CONTENT), f"audio/{file_extension[1:]}")
        }
        data = {"language": "ru"}

        response = client.post("/transcribe", files=files, data=data)

        assert response.status_code == 200
        result = response.json()

        assert result["status"] == "success"
        assert result["message"] == "Audio successfully transcribed"
        assert "transcription_id" in result
        # Исправляем: в ответе нет поля 'language', проверяем другое
        assert "filename" in result
        assert result["text_length"] > 0
        assert "download_url" in result

    def test_transcribe_invalid_file_extension(self):
        """Тест с недопустимым расширением файла"""
        files = {
            "file": ("test.txt", io.BytesIO(b"text file"), "text/plain")
        }
        data = {"language": "ru"}

        response = client.post("/transcribe", files=files, data=data)

        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        assert "detail" in error_data
        assert "Unsupported file extension" in error_data["detail"]

    def test_transcribe_missing_file(self):
        """Тест без файла"""
        data = {"language": "ru"}

        response = client.post("/transcribe", data=data)

        assert response.status_code == 422  # Validation error

    def test_download_transcription_success(self, mock_transcription_service):
        """Тест успешного скачивания транскрипции"""
        # Сначала создаем транскрипцию
        files = {"file": ("test.mp3", io.BytesIO(TEST_AUDIO_CONTENT), "audio/mp3")}
        transcribe_response = client.post("/transcribe", files=files, data={"language": "ru"})
        result = transcribe_response.json()
        transcription_id = result["transcription_id"]

        # Затем скачиваем
        download_response = client.get(f"/transcriptions/{transcription_id}/download")

        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith("text/plain")
        assert "transcription_" in download_response.headers["content-disposition"]

    def test_download_nonexistent_transcription(self):
        """Тест скачивания несуществующей транскрипции"""
        response = client.get(f"/transcriptions/{TEST_UUID}/download")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "Transcription file not found" in data["detail"]

    def test_transcribe_large_file(self, mock_transcription_service):
        """Тест с большим файлом (симуляция)"""
        # Создаем большой файл (10MB)
        large_content = b"x" * (10 * 1024 * 1024)
        files = {
            "file": ("large.mp3", io.BytesIO(large_content), "audio/mp3")
        }
        data = {"language": "ru"}

        response = client.post("/transcribe", files=files, data=data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_concurrent_transcriptions(self, mock_transcription_service):
        """Тест параллельных запросов транскрибирования"""
        import threading
        import concurrent.futures

        results = []

        def transcribe_audio():
            files = {"file": ("test.mp3", io.BytesIO(TEST_AUDIO_CONTENT), "audio/mp3")}
            response = client.post("/transcribe", files=files, data={"language": "ru"})
            results.append(response.status_code)

        # Запускаем 5 параллельных запросов
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(transcribe_audio) for _ in range(5)]
            concurrent.futures.wait(futures)

        # Проверяем что все запросы успешны
        assert all(status == 200 for status in results)

class TestTranscriptionService:
    """Тесты для сервиса транскрибирования"""

    def test_save_upload_file(self, tmp_path):
        """Тест сохранения загруженного файла"""
        service = TranscriptionService()
        service.upload_dir = tmp_path

        # Создаем мок файл
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test_audio.mp3"
        mock_file.read = AsyncMock(return_value=TEST_AUDIO_CONTENT)

        # Сохраняем файл
        file_path, file_id = asyncio.run(service.save_upload_file(mock_file))

        assert file_path.exists()
        assert file_path.parent == tmp_path
        assert file_path.suffix == ".mp3"
        assert len(file_id) > 0

        # Проверяем содержимое файла
        with open(file_path, "rb") as f:
            assert f.read() == TEST_AUDIO_CONTENT

    def test_save_upload_file_no_filename(self, tmp_path):
        """Тест сохранения файла без имени"""
        service = TranscriptionService()
        service.upload_dir = tmp_path

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = None
        mock_file.read = AsyncMock(return_value=TEST_AUDIO_CONTENT)

        file_path, file_id = asyncio.run(service.save_upload_file(mock_file))

        assert file_path.exists()
        assert file_path.suffix == ".wav"

    @patch('app.services.whisper.load_model')
    def test_transcribe_audio_success(self, mock_load_model, tmp_path):
        """Тест успешного транскрибирования аудио"""
        service = TranscriptionService()

        # Мокаем модель whisper
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": TEST_TRANSCRIPTION_TEXT}
        mock_load_model.return_value = mock_model

        # Создаем тестовый аудиофайл
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_bytes(TEST_AUDIO_CONTENT)

        # Транскрибируем
        result = service.transcribe_audio(audio_file, "ru")

        assert result == TEST_TRANSCRIPTION_TEXT
        mock_load_model.assert_called_once()
        mock_model.transcribe.assert_called_once_with(
            str(audio_file),
            language="ru",
            fp16=False
        )

    def test_transcribe_audio_file_not_found(self):
        """Тест транскрибирования несуществующего файла"""
        service = TranscriptionService()

        with pytest.raises(FileNotFoundError):
            service.transcribe_audio(Path("/nonexistent/file.wav"), "ru")

    def test_save_transcription_text(self, tmp_path):
        """Тест сохранения текста транскрипции"""
        service = TranscriptionService()
        service.output_dir = tmp_path

        file_id = TEST_UUID
        text = TEST_TRANSCRIPTION_TEXT

        # Сохраняем текст
        file_path = service.save_transcription_text(file_id, text)

        assert file_path.exists()
        assert file_path.name == f"{file_id}_transcription.txt"
        assert file_path.parent == tmp_path

        # Проверяем содержимое
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == text

    @patch('app.services.httpx.AsyncClient')
    def test_send_to_external_api_success(self, mock_async_client):
        """Тест успешной отправки во внешний API"""
        service = TranscriptionService()

        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response

        mock_async_client.return_value = mock_client_instance

        # Отправляем
        result = asyncio.run(service.send_to_external_api(TEST_UUID, TEST_TRANSCRIPTION_TEXT))

        assert result["status"] == "success"
        assert result["external_api_response"]["status_code"] == 200

    def test_cleanup_files(self, tmp_path):
        """Тест очистки временных файлов"""
        service = TranscriptionService()

        # Создаем тестовые файлы
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("test1")
        file2.write_text("test2")

        # Очищаем
        service.cleanup_files(file1, file2)

        # Проверяем что файлы удалены
        assert not file1.exists()
        assert not file2.exists()


# Фикстуры pytest
@pytest.fixture
def mock_transcription_service():
    """Фикстура для мока сервиса транскрибирования"""
    with patch('app.main.transcription_service') as mock_service:
        # Настраиваем мок
        mock_service.save_upload_file = AsyncMock(
            return_value=(Path("/tmp/test_audio.mp3"), TEST_UUID)
        )
        mock_service.transcribe_audio = MagicMock(
            return_value=TEST_TRANSCRIPTION_TEXT
        )
        mock_service.save_transcription_text = MagicMock(
            return_value=Path(f"/tmp/test_outputs/{TEST_UUID}_transcription.txt")
        )
        mock_service.send_to_external_api = AsyncMock(
            return_value={
                "status": "success",
                "external_api_response": {"message": "Success", "status_code": 200}
            }
        )
        mock_service.cleanup_files = MagicMock()

        # Мокаем проверку существования файла для скачивания
        mock_output_dir = MagicMock()
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_output_dir.__truediv__.return_value = mock_file
        mock_service.output_dir = mock_output_dir

        yield mock_service


class TestPerformance:
    """Тесты производительности"""

    def test_response_time(self, mock_transcription_service):
        """Тест времени отклика API"""
        import time

        files = {"file": ("test_perf.mp3", io.BytesIO(TEST_AUDIO_CONTENT), "audio/mp3")}

        start_time = time.time()
        response = client.post("/transcribe", files=files, data={"language": "ru"})
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        # Проверяем что ответ получен за разумное время
        assert response_time < 10.0  # 10 секунд максимум

    def test_memory_usage(self, mock_transcription_service):
        """Тест использования памяти (симуляция)"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Выполняем несколько запросов
        for i in range(5):
            files = {"file": (f"test_{i}.mp3", io.BytesIO(TEST_AUDIO_CONTENT), "audio/mp3")}
            response = client.post("/transcribe", files=files, data={"language": "ru"})
            assert response.status_code == 200

        final_memory = process.memory_info().rss / 1024 / 1024

        # Проверяем что утечек памяти нет
        memory_increase = final_memory - initial_memory
        assert memory_increase < 100  # Увеличение не более 100MB

if __name__ == "__main__":
    pytest.main([__file__, "-v"])