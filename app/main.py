from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import uuid
from datetime import datetime
import asyncio
from pathlib import Path

from app.config import settings
from app.models import TranscriptionRequest, TranscriptionResponse, ErrorResponse
from app.services import transcription_service

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "endpoints": {
            "transcribe": "POST /transcribe",
            "download": "GET /transcriptions/{transcription_id}/download",
            "health": "GET /health"
        }
    }


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(..., description="Audio file to transcribe"),
        language: str = Form("ru", description="Language code (e.g., 'ru', 'en')"),
):
    """
    Транскрибирование аудиофайла в текст

    Поддерживаемые форматы: MP3, WAV, M4A, FLAC и другие поддерживаемые Whisper
    """
    try:
        print(f"\n🎤 Starting transcription request")
        print(f"Filename: {file.filename}")
        print(f"Content type: {file.content_type}")
        print(f"Language: {language}")

        filename = file.filename or "audio"
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4', '.webm',
                              '.aac', '.wma', '.aiff', '.opus', '.mpeg', '.amr'}

        # Получаем расширение файла
        file_ext = Path(filename).suffix.lower()

        if file_ext not in allowed_extensions:
            error_msg = f"Unsupported file extension: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )

        # Генерируем ID для транскрипции
        transcription_id = str(uuid.uuid4())
        print(f"Transcription ID: {transcription_id}")

        # Сохраняем загруженный файл
        audio_path, file_id = await transcription_service.save_upload_file(file)

        # Транскрибируем аудио
        text = transcription_service.transcribe_audio(audio_path, language)

        # Сохраняем текст в файл
        text_file_path = transcription_service.save_transcription_text(
            file_id, text
        )

        # Создаем URL для скачивания
        download_url = f"/transcriptions/{file_id}/download"

        # Отправляем во внешний API (в фоне)
        background_tasks.add_task(
            transcription_service.send_to_external_api,
            transcription_id,
            text
        )

        background_tasks.add_task(
            transcription_service.cleanup_files,
            audio_path
        )

        return TranscriptionResponse(
            status="success",
            message="Audio successfully transcribed",
            transcription_id=transcription_id,
            filename=filename,
            text_length=len(text),
            download_url=download_url,
            external_api_status="pending",
            created_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )

@app.get("/transcriptions/{transcription_id}/download")
async def download_transcription(transcription_id: str):
    """
    Скачивание файла с транскрипцией
    """
    file_path = transcription_service.output_dir / f"{transcription_id}_transcription.txt"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Transcription file not found"
        )

    return FileResponse(
        path=file_path,
        filename=f"transcription_{transcription_id}.txt",
        media_type="text/plain"
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP Exception",
            detail=exc.detail
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )