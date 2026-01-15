from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import uuid

Base = declarative_base()


class TranscriptionRecord(Base):
    """Запись о транскрипции"""
    __tablename__ = "transcription_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer)  # в байтах
    duration = Column(Float)  # в секундах
    language = Column(String(10), default="auto")
    status = Column(String(20), default="started")  # started, completed, error
    error_message = Column(Text, nullable=True)

    # Результаты
    text_length = Column(Integer)
    processing_time = Column(Float)  # время обработки в секундах
    confidence_score = Column(Float)  # оценка уверенности Whisper

    # Системная информация
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    transcription_id = Column(String(255), nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Связи
    word_statistics = relationship("WordStatistic", back_populates="transcription", cascade="all, delete-orphan")
    performance_metrics = relationship("PerformanceMetric", back_populates="transcription",
                                       cascade="all, delete-orphan")


class WordStatistic(Base):
    """Статистика по словам"""
    __tablename__ = "word_statistics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transcription_id = Column(String, ForeignKey("transcription_records.id", ondelete="CASCADE"))
    word = Column(String(100), nullable=False)
    count = Column(Integer, default=1)
    language = Column(String(10))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Связи
    transcription = relationship("TranscriptionRecord", back_populates="word_statistics")


class PerformanceMetric(Base):
    """Метрики производительности"""
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transcription_id = Column(String, ForeignKey("transcription_records.id", ondelete="CASCADE"))
    metric_name = Column(String(50), nullable=False)  # transcription_time, audio_duration, etc
    metric_value = Column(Float, nullable=False)
    unit = Column(String(20), default="seconds")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Связи
    transcription = relationship("TranscriptionRecord", back_populates="performance_metrics")


class SystemMetric(Base):
    """Системные метрики"""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    metric_type = Column(String(50), nullable=False)  # cpu_usage, memory_usage, active_requests
    metric_value = Column(Float, nullable=False)
    service = Column(String(50), default="transcription")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))