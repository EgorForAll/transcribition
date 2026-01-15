import uuid
from pathlib import Path
from datetime import datetime, timezone
import httpx
import whisper
import os
from typing import Tuple
from app.config import settings


class TranscriptionService:
    """Сервис для транскрипции аудио"""

    def __init__(self):
        self.model = None
        self.upload_dir = settings.upload_dir_path
        self.output_dir = settings.output_dir_path
        self.external_api_url = settings.EXTERNAL_API_URL
        self.external_api_timeout = settings.EXTERNAL_API_TIMEOUT
        self.external_api_enabled = settings.EXTERNAL_API_ENABLED

        # Создаем директории если их нет
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def load_model(self):
        """Загрузка модели Whisper"""
        if self.model is None:
            print(f"🤖 Loading Whisper model: {settings.WHISPER_MODEL}")
            self.model = whisper.load_model(settings.WHISPER_MODEL, device=settings.WHISPER_DEVICE)
            print("✅ Whisper model loaded")
        return self.model

    async def save_upload_file(self, file) -> Tuple[Path, str]:
        """
        Сохранение загруженного файла
        """
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower() if file.filename else '.mp3'
        filename = f"{file_id}{file_ext}"
        file_path = self.upload_dir / filename

        # Сохраняем файл
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)

        print(f"💾 File saved: {file_path}")
        return file_path, file_id

    def transcribe_audio(self, audio_path: Path, language: str = "ru") -> str:
        """
        Транскрибирование аудиофайла
        """
        print(f"🎤 Transcribing audio: {audio_path}")

        start_time = datetime.now(timezone.utc)

        try:
            # Загружаем модель если еще не загружена
            model = self.load_model()

            # Транскрибируем
            result = model.transcribe(
                str(audio_path),
                language=language if language != "auto" else None,
                fp16=False
            )

            text = result.get("text", "").strip()
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            print(f"✅ Transcription completed in {processing_time:.2f}s")
            print(f"📝 Text length: {len(text)} characters")
            return text

        except Exception as e:
            print(f"❌ Transcription error: {e}")
            raise Exception(f"Transcription failed: {str(e)}")

    def save_transcription_text(self, file_id: str, text: str) -> Path:
        """
        Сохранение текста транскрипции в файл
        """
        filename = f"{file_id}_transcription.txt"
        file_path = self.output_dir / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)

        print(f"💾 Transcription saved: {file_path}")
        return file_path

    async def send_to_external_api(self, transcription_id: str, text: str) -> bool:
        """
        Отправка транскрипции во внешний API
        """
        if not self.external_api_enabled:
            print("⚠️ External API is disabled")
            return False

        print(f"🌍 Sending to external API: {self.external_api_url}")

        try:
            async with httpx.AsyncClient(timeout=self.external_api_timeout) as client:
                payload = {
                    "transcription_id": transcription_id,
                    "text": text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "service": settings.APP_NAME
                }

                response = await client.post(self.external_api_url, json=payload)

                if response.status_code == 200:
                    print(f"✅ Successfully sent to external API")
                    return True
                else:
                    print(f"❌ External API error: {response.status_code}")
                    return False

        except Exception as e:
            print(f"❌ External API error: {e}")
            return False

    async def cleanup_files(self, audio_path: Path):
        """
        Очистка временных файлов
        """
        try:
            if audio_path.exists():
                os.remove(audio_path)
                print(f"🗑️ Cleaned up audio file: {audio_path}")
        except Exception as e:
            print(f"⚠️ Error cleaning up files: {e}")


transcription_service = TranscriptionService()