import os
import uuid
import whisper
import httpx
from pathlib import Path
from typing import Tuple, Optional
import asyncio
from fastapi import UploadFile

from app.config import settings


class TranscriptionService:
    def __init__(self):
        self.model = None
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.output_dir = Path(settings.OUTPUT_DIR)

        # Создаем директории если их нет
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def load_model(self):
        if self.model is None:
            print(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            self.model = whisper.load_model(settings.WHISPER_MODEL)
        return self.model

    async def save_upload_file(self, file: UploadFile) -> Tuple[Path, str]:
        file_id = str(uuid.uuid4())
        original_filename = file.filename or "audio"
        ext = original_filename.split('.')[-1] if '.' in original_filename else 'wav'

        filename = f"{file_id}.{ext}"
        file_path = self.upload_dir / filename

        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return file_path, file_id

    def transcribe_audio(self, audio_path: Path, language: str = "ru") -> str:
        model = self.load_model()

        # Транскрибируем
        result = model.transcribe(
            str(audio_path),
            language=language,
            fp16=False
        )

        return result["text"]

    def save_transcription_text(self, file_id: str, text: str) -> Path:
        filename = f"{file_id}_transcription.txt"
        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        return file_path

    async def send_to_external_api(self, transcription_id: str, text: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=settings.EXTERNAL_API_TIMEOUT) as client:
                payload = {
                    "transcription_id": transcription_id,
                    "text": text,
                    "text_length": len(text),
                    "status": "completed"
                }

                # В реальном проекте здесь будет реальный вызов API
                # response = await client.post(settings.EXTERNAL_API_URL, json=payload)

                await asyncio.sleep(1)

                return {
                    "status": "success",
                    "external_api_response": {
                        "message": "Transcription successfully received",
                        "id": str(uuid.uuid4()),
                        "status_code": 200
                    }
                }

        except Exception as e:
            return {
                "status": "error",
                "external_api_response": {
                    "message": f"Failed to send to external API: {str(e)}",
                    "status_code": 500
                }
            }

    def cleanup_files(self, *paths):
        for path in paths:
            try:
                if path and path.exists():
                    path.unlink()
            except Exception as e:
                print(f"Error deleting file {path}: {e}")


transcription_service = TranscriptionService()