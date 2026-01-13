import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Настройки приложения
    APP_NAME: str = "Transcribition Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Настройки модели Whisper
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")

    # Настройки путей
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")

    # Настройки внешнего API (симуляция)
    EXTERNAL_API_URL: str = os.getenv("EXTERNAL_API_URL", "https://example.org/post")
    EXTERNAL_API_TIMEOUT: int = int(os.getenv("EXTERNAL_API_TIMEOUT", "30"))

    # Настройки сервера
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    class Config:
        env_file = ".env"


settings = Settings()