from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
import contextlib

# Создаем подключение к базе данных
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    pool_recycle=3600,  # Переподключение каждые час
    pool_size=10,       # Размер пула соединений
    max_overflow=20     # Максимальное количество соединений
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()


def get_db():
    """
    Зависимость для FastAPI Dependency Injection
    Используется в эндпоинтах
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextlib.contextmanager
def get_db_session():
    """
    Контекстный менеджер для работы с сессией БД
    Используется вне FastAPI контекста
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """Проверка подключения к БД"""
    try:
        # Используем контекстный менеджер для безопасного подключения
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def init_db():
    """Инициализация базы данных (создание таблиц)"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        raise