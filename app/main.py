from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, status, Depends
from fastapi.responses import FileResponse, JSONResponse
import uuid
from datetime import datetime, timezone
from pathlib import Path
import traceback

from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from app.analytics.service import AnalyticsService
from app.config import settings
from app.models import TranscriptionResponse, ErrorResponse
from app.transcribition import transcription_service
from app.database import get_db, check_db_connection, engine
from app.redis_client import redis_client

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "endpoints": {
            "transcribe": "POST /transcribe",
            "download": "GET /transcriptions/{file_id}/download",
            "health": "GET /health"
        }
    }


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(..., description="Audio file to transcribe"),
        language: str = Form("ru", description="Language code (e.g., 'ru', 'en')"),
        db: Session = Depends(get_db)
):
    """
    Транскрибирование аудиофайла в текст
    """
    file_id = None
    analytics_service = None

    try:
        print(f"\n🎤 Starting transcription request")
        print(f"Filename: {file.filename}")
        print(f"Content type: {file.content_type}")
        print(f"Language: {language}")

        # Проверяем, включена ли аналитика
        print(f"📊 ANALYTICS_ENABLED: {settings.ANALYTICS_ENABLED}")

        filename = file.filename or "audio"
        allowed_extensions = {
            # Аудио форматы
            '.mp3', '.wav', '.m4a', '.flac', '.ogg',
            '.aac', '.wma', '.aiff', '.opus', '.amr',

            # Видео форматы (извлекается аудио дорожка)
            '.mp4', '.webm', '.avi', '.mkv', '.mov',
            '.wmv', '.flv', '.mpeg', '.mpg', '.3gp',

            # Другие форматы
            '.m4v', '.ogv', '.ts', '.m2ts'
        }

        # Получаем расширение файла
        file_ext = Path(filename).suffix.lower()

        if file_ext not in allowed_extensions:
            error_msg = f"Unsupported file extension: {file_ext}. Allowed: {', '.join(sorted(allowed_extensions))}"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )

        # Генерируем ID для транскрипции
        transcription_id = str(uuid.uuid4())
        print(f"Transcription ID: {transcription_id}")

        file_content = await file.read()
        file_size = len(file_content)
        print(f"📏 File size: {file_size} bytes")

        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(file_content)
            temp_path = tmp.name

        from io import BytesIO
        file.file = BytesIO(file_content)
        file.file.seek(0)

        # Сохраняем загруженный файл
        audio_path, file_id = await transcription_service.save_upload_file(file)
        print(f"✅ File saved. File ID: {file_id}, Path: {audio_path}")

        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        analytics_service = AnalyticsService(db)
        if settings.ANALYTICS_ENABLED and analytics_service:
            try:
                print(f"📊 Attempting to record transcription start for file_id: {file_id}")

                from pydub import AudioSegment
                try:
                    audio = AudioSegment.from_file(audio_path)
                    duration = len(audio) / 1000.0  # в секундах
                    print(f"⏱️ Audio duration: {duration:.2f} seconds")
                except Exception as e:
                    print(f"⚠️ Could not get audio duration: {e}")
                    duration = 0.0

                record_data = {
                    'file_uuid': file_id,
                    'filename': filename,
                    'file_size': file_size,
                    'duration': duration,
                    'language': language,
                    'transcription_id': transcription_id
                }
                print(f"📊 Record data: {record_data}")

                # Сохраняем запись и получаем ID
                record_uuid = analytics_service.record_transcription_start(record_data)
                print(f"📊 Database record created: UUID={record_uuid}")

            except Exception as e:
                print(f"❌ Failed to record start in database: {e}")
                traceback.print_exc()
        else:
            print("📊 Analytics is disabled, skipping database recording")

        # Транскрибируем аудио
        text = ""
        start_time = datetime.now(timezone.utc)

        try:
            text = transcription_service.transcribe_audio(audio_path, language)
            print(f"✅ Transcription completed. Text length: {len(text)} chars")

            # Если текст пустой, пробуем другой язык
            if not text or len(text.strip()) == 0:
                print(f"⚠️ Текст пустой! Пробуем автоопределение языка...")
                try:
                    # Пробуем без указания языка
                    text = transcription_service.transcribe_audio(audio_path, "auto")
                    print(f"🔁 Результат с автоопределением: {len(text)} chars")

                    # Если все еще пусто
                    if not text or len(text.strip()) == 0:
                        print(f"⚠️ Все еще пусто! Пробуем английский...")
                        text = transcription_service.transcribe_audio(audio_path, "en")
                        print(f"🔁 Результат на английском: {len(text)} chars")

                        # Если все еще пусто, создаем сообщение об ошибке
                        if not text or len(text.strip()) == 0:
                            text = "Текст не распознан. Возможно, аудио слишком тихое, поврежденное или содержит только музыку/шум."
                except Exception as e:
                    print(f"⚠️ Ошибка при повторной попытке транскрипции: {e}")
                    text = "Ошибка транскрипции. Проверьте аудиофайл."

        except Exception as e:
            print(f"❌ Transcription error: {e}")
            if settings.ANALYTICS_ENABLED and file_id and analytics_service:
                try:
                    analytics_service.record_transcription_error(file_id, str(e))
                except Exception:
                    pass
            raise HTTPException(status_code=500, detail=str(e))

        # Рассчитываем время обработки
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Завершение транскрипции
        if settings.ANALYTICS_ENABLED and analytics_service and file_id:
            try:
                print(f"📊 Attempting to record transcription completion for file_uuid: {file_id}")

                success = analytics_service.record_transcription_complete(file_id, {
                    'text_length': len(text),
                    'processing_time': processing_time,
                    'confidence_score': 0.95,
                    'status': 'completed'
                })
                if success:
                    print(f"📊 Database updated with completion")
                else:
                    print(f"⚠️ Failed to update database with completion (no rows affected)")
            except Exception as e:
                print(f"⚠️ Failed to record completion in database: {e}")
                traceback.print_exc()
        else:
            print("📊 Analytics is disabled, skipping database update")

        # Статистика слов
        if settings.ANALYTICS_ENABLED and text and len(text.strip()) > 0 and analytics_service and file_id:
            try:
                import re
                words = re.findall(r'\b\w+\b', text.lower())
                from collections import Counter
                word_counts = Counter(words)

                word_stats = [{
                    'word': word,
                    'count': count,
                    'language': language
                } for word, count in word_counts.items() if len(word) > 2]

                if word_stats:
                    analytics_service.add_word_statistics(file_id, word_stats)
                    print(f"📊 Added {len(word_stats)} word statistics")
            except Exception as e:
                print(f"⚠️ Error collecting word statistics: {e}")

        # Добавляем метрику производительности
        if settings.ANALYTICS_ENABLED and analytics_service and file_id:
            try:
                analytics_service.add_performance_metric(file_id, 'transcription_time', processing_time)
                print(f"📊 Added performance metric: transcription_time = {processing_time:.2f}s")
            except Exception as e:
                print(f"⚠️ Error adding performance metric: {e}")

        # Сохраняем текст в файл
        text_file_path = transcription_service.save_transcription_text(file_id, text)
        print(f"💾 Text saved to: {text_file_path}")

        # Создаем URL для скачивания
        download_url = f"/transcriptions/{file_id}/download"
        print(f"🔗 Download URL: {download_url}")

        # Отправляем во внешний API (для симуляции)
        if settings.EXTERNAL_API_ENABLED:
            print(f"🌍 External API is enabled, adding background task")
            background_tasks.add_task(
                transcription_service.send_to_external_api,
                transcription_id,
                text
            )
        else:
            print(f"🌍 External API is disabled")

        # Очистка файлов (в фоне)
        background_tasks.add_task(
            transcription_service.cleanup_files,
            audio_path
        )

        response = TranscriptionResponse(
            status="success",
            message="Audio successfully transcribed",
            transcription_id=transcription_id,
            filename=filename,
            text_length=len(text),
            download_url=download_url,
            external_api_status="pending",
            created_at=datetime.now(timezone.utc)
        )

        print(f"✅ Request completed successfully")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()

        # ЗАПИСЬ ОБЩЕЙ ОШИБКИ В БАЗУ
        if settings.ANALYTICS_ENABLED and file_id and analytics_service:
            try:
                print(f"📊 Attempting to record error for file_id: {file_id}")
                analytics_service.record_transcription_error(file_id, f"Endpoint error: {str(e)}")
            except Exception as db_error:
                print(f"⚠️ Failed to record error in database: {db_error}")

        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {},
            "version": settings.VERSION
        }

        # Проверка базы данных
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                db_ok = result.scalar() == 1
                health_data["services"]["database"] = {
                    "status": "connected" if db_ok else "disconnected",
                    "ok": db_ok
                }
                print(f"📊 Database connection check: {db_ok}")
        except Exception as e:
            health_data["services"]["database"] = {
                "status": "error",
                "ok": False,
                "error": str(e)[:100]  # Обрезаем длинные сообщения
            }
            print(f"❌ Database check error: {e}")

        # Проверка Redis
        try:
            if settings.REDIS_ENABLED:
                if redis_client.redis_client:
                    redis_ok = redis_client.redis_client.ping()
                    health_data["services"]["redis"] = {
                        "status": "connected" if redis_ok else "disconnected",
                        "ok": redis_ok,
                        "host": settings.REDIS_HOST,
                        "port": settings.REDIS_PORT
                    }
                    print(f"🔴 Redis connection check: {redis_ok}")
                else:
                    health_data["services"]["redis"] = {
                        "status": "not_initialized",
                        "ok": False,
                        "error": "Redis client not initialized"
                    }
                    print(f"🔴 Redis client not initialized")
            else:
                health_data["services"]["redis"] = {
                    "status": "disabled",
                    "ok": True,  # Redis может быть отключен
                    "enabled": False
                }
                print(f"🔴 Redis is disabled")
        except Exception as e:
            health_data["services"]["redis"] = {
                "status": "error",
                "ok": False,
                "error": str(e)[:100]
            }
            print(f"🔴 Redis check error: {e}")

        # Проверка директорий
        try:
            upload_dir_ok = settings.upload_dir_path.exists()
            output_dir_ok = settings.output_dir_path.exists()

            health_data["services"]["upload_dir"] = {
                "status": "exists" if upload_dir_ok else "missing",
                "ok": upload_dir_ok,
                "path": str(settings.upload_dir_path)
            }
            health_data["services"]["output_dir"] = {
                "status": "exists" if output_dir_ok else "missing",
                "ok": output_dir_ok,
                "path": str(settings.output_dir_path)
            }

            print(f"📁 Upload directory exists: {upload_dir_ok}")
            print(f"📁 Output directory exists: {output_dir_ok}")
        except Exception as e:
            health_data["services"]["upload_dir"] = {
                "status": "error",
                "ok": False,
                "error": str(e)[:100]
            }
            health_data["services"]["output_dir"] = {
                "status": "error",
                "ok": False,
                "error": str(e)[:100]
            }
            print(f"❌ Directory check error: {e}")

        # Определяем общий статус
        required_services_ok = (
                health_data["services"].get("database", {}).get("ok", False) and
                health_data["services"].get("upload_dir", {}).get("ok", False) and
                health_data["services"].get("output_dir", {}).get("ok", False)
        )

        health_data["status"] = "healthy" if required_services_ok else "unhealthy"

        status_code = 200 if required_services_ok else 503

        return JSONResponse(
            status_code=status_code,
            content=health_data
        )

    except Exception as e:
        print(f"❌ Health check critical error: {e}")
        import traceback
        traceback.print_exc()

        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Health check failed",
                "details": str(e)[:200],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@app.get("/transcriptions/{file_id}/download")
async def download_transcription(file_id: str):
    """
    Скачивание файла с транскрипцией
    """
    file_path = transcription_service.output_dir / f"{file_id}_transcription.txt"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Transcription file not found"
        )

    return FileResponse(
        path=file_path,
        filename=f"transcription_{file_id}.txt",
        media_type="text/plain"
    )


@app.get("/analytics/overview")
async def get_analytics_overview(db: Session = Depends(get_db)):
    """Получение обзора аналитики"""
    if not settings.ANALYTICS_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Analytics is disabled"
        )

    try:
        analytics_service = AnalyticsService(db)
        overview = analytics_service.get_system_overview()

        return {
            "status": "success",
            "data": overview,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics: {str(e)}"
        )


@app.get("/analytics/test")
async def test_analytics(db: Session = Depends(get_db)):
    """Тестовый endpoint для аналитики"""
    try:
        from sqlalchemy import text

        # Простой запрос для проверки
        result = db.execute(text("SELECT COUNT(*) FROM transcription_records"))
        count = result.fetchone()[0]

        return {
            "status": "success",
            "record_count": count,
            "message": "Analytics database is accessible"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.exception_handler(HTTPException)
async def http_exception_handler(exc):
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