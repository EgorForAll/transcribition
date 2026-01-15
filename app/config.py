from pathlib import Path
import os


class Settings:
    """Временные фиксированные настройки"""

    def __init__(self):
        #  База данных 
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://transcription_user:transcription_password@localhost:5432/transcription_db"
        )

        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "transcription_db")
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "transcription_user")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "transcription_password")

        # Аналитика
        self.ANALYTICS_ENABLED = self._str_to_bool(os.getenv("ANALYTICS_ENABLED", "true"))

        #  Redis 
        self.REDIS_HOST = os.getenv("REDIS_HOST", "redis")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
        self.REDIS_ENABLED = self._str_to_bool(os.getenv("REDIS_ENABLED", "false"))

        #  Приложение 
        self.APP_NAME = os.getenv("APP_NAME", "Audio Transcription Service")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))
        self.DEBUG = self._str_to_bool(os.getenv("DEBUG", "true"))

        #  Whisper 
        self.WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
        self.WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

        #  Пути 
        self.BASE_DIR = Path(__file__).parent.parent
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
        self.OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")

        # Создаем директории
        self._create_directories()

        #  Внешний API 
        self.EXTERNAL_API_URL = os.getenv("EXTERNAL_API_URL", "")
        self.EXTERNAL_API_TIMEOUT = int(os.getenv("EXTERNAL_API_TIMEOUT", "30"))
        self.EXTERNAL_API_ENABLED = self._str_to_bool(os.getenv("EXTERNAL_API_ENABLED", "false"))

        #  Безопасность 
        self.SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self.API_KEYS = self._parse_api_keys(os.getenv("API_KEYS", ""))

        # Выводим информацию о загрузке
        self._print_settings()

    @property
    def upload_dir_path(self) -> Path:
        """Полный путь к директории загрузок"""
        return self.BASE_DIR / self.UPLOAD_DIR

    @property
    def output_dir_path(self) -> Path:
        """Полный путь к директории результатов"""
        return self.BASE_DIR / self.OUTPUT_DIR

    def _str_to_bool(self, value: str) -> bool:
        """Конвертация строки в булево значение"""
        if isinstance(value, bool):
            return value
        return value.lower() in ("true", "1", "yes", "on", "t")

    def _parse_api_keys(self, value: str) -> list:
        """Парсинг API ключей"""
        if not value:
            return []
        value = value.strip().strip('"').strip("'")
        return [key.strip() for key in value.split(",") if key.strip()]

    def _create_directories(self):
        """Создание необходимых директорий"""
        try:
            self.upload_dir_path.mkdir(exist_ok=True)
            self.output_dir_path.mkdir(exist_ok=True)
            print(f"✅ Директории созданы/проверены")
            print(f"   📁 Загрузки: {self.upload_dir_path}")
            print(f"   📁 Результаты: {self.output_dir_path}")
        except Exception as e:
            print(f"⚠️ Ошибка при создании директорий: {e}")

    def _print_settings(self):
        """Вывод информации о настройках"""
        print("\n" + "=" * 60)
        print("⚙️  НАСТРОЙКИ ПРИЛОЖЕНИЯ")
        print("=" * 60)

        # Маскируем пароли в DATABASE_URL
        masked_db_url = self.DATABASE_URL
        if "://" in masked_db_url:
            protocol, rest = masked_db_url.split("://", 1)
            if "@" in rest:
                credentials, server = rest.split("@", 1)
                if ":" in credentials:
                    user, password = credentials.split(":", 1)
                    masked_credentials = f"{user}:*****"
                    masked_db_url = f"{protocol}://{masked_credentials}@{server}"

        print(f"📱 Приложение: {self.APP_NAME} v{self.VERSION}")
        print(f"🌐 Сервер: {self.HOST}:{self.PORT}")
        print(f"🔧 Режим отладки: {self.DEBUG}")
        print(f"🗄️  База данных: {masked_db_url}")
        print(f"📊 Аналитика включена: {self.ANALYTICS_ENABLED}")
        print(f"🤖 Модель Whisper: {self.WHISPER_MODEL} ({self.WHISPER_DEVICE})")
        print(f"🔑 API ключей: {len(self.API_KEYS)}")
        print("=" * 60 + "\n")

    def validate(self) -> bool:
        """Валидация настроек"""
        errors = []

        # Проверка базы данных
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL не указан")

        # Проверка директорий
        if not self.upload_dir_path.exists():
            errors.append(f"Директория uploads не существует: {self.upload_dir_path}")
        if not self.output_dir_path.exists():
            errors.append(f"Директория outputs не существует: {self.output_dir_path}")

        if errors:
            print("❌ Ошибки в настройках:")
            for error in errors:
                print(f"   - {error}")
            return False

        print("✅ Настройки валидны")
        return True

    def get_db_params(self) -> dict:
        """Получение параметров для подключения к БД без DATABASE_URL"""
        return {
            "host": self.POSTGRES_HOST,
            "port": self.POSTGRES_PORT,
            "database": self.POSTGRES_DB,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD
        }

settings = Settings()