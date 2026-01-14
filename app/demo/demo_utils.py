import uuid
from pathlib import Path
import json
from datetime import datetime


class DemoUtils:
    """Утилиты для демо-стенда"""

    @staticmethod
    def generate_sample_text(language="ru"):
        """Генерация демо-текста"""
        samples = {
            "ru": "Это пример транскрибированного текста на русском языке. "
                  "Сервис успешно преобразовал аудиозапись в текстовый формат "
                  "с высокой точностью распознавания речи.",
            "en": "This is an example of transcribed text in English. "
                  "The service has successfully converted audio recording "
                  "to text format with high speech recognition accuracy."
        }
        return samples.get(language, samples["en"])

    @staticmethod
    def create_demo_response(filename="audio.mp3"):
        """Создание демо-ответа API"""
        return {
            "status": "success",
            "message": "Audio successfully transcribed",
            "transcription_id": str(uuid.uuid4()),
            "filename": filename,
            "text": DemoUtils.generate_sample_text(),
            "text_length": 150,
            "download_url": f"/transcriptions/{uuid.uuid4()}/download",
            "external_api_status": "completed",
            "created_at": datetime.now().isoformat()
        }