from typing import Dict, Any
import psutil
import time
from fastapi import logger
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import threading
from app.analytics.repository import AnalyticsRepository


class AnalyticsService:
    def __init__(self, db: Session):
        self.repository = AnalyticsRepository(db)
        self._start_system_metrics_collection()

    def _start_system_metrics_collection(self):
        """Запуск сбора системных метрик в фоне"""
        def collect_metrics():
            while True:
                try:
                    # Собираем метрики системы
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()

                    # Сохраняем метрики
                    system_metrics = [
                        {
                            'metric_type': 'cpu_usage',
                            'metric_value': cpu_percent,
                            'service': 'transcription'
                        },
                        {
                            'metric_type': 'memory_usage',
                            'metric_value': memory.percent,
                            'service': 'transcription'
                        },
                        {
                            'metric_type': 'memory_available',
                            'metric_value': memory.available / 1024 / 1024,  # MB
                            'service': 'transcription'
                        }
                    ]

                    # Сохраняем в БД
                    for metric in system_metrics:
                        self.repository.add_system_metric(metric)

                    # Ждем 60 секунд перед следующим сбором
                    time.sleep(60)

                except Exception as e:
                    print(f"⚠️ Error collecting system metrics: {e}")
                    time.sleep(60)

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=collect_metrics, daemon=True)
        thread.start()
        print("📊 System metrics collection started")

    def record_transcription_complete(self, file_uuid: str, data: Dict[str, Any]) -> bool:
        """Запись завершения транскрипции с метриками"""
        try:
            # Обновляем запись транскрипции
            success = self.repository.update_transcription_record(file_uuid, {
                **data,
                'completed_at': datetime.now(timezone.utc),
                'status': 'completed'
            })

            if success and 'processing_time' in data:
                # Добавляем метрику производительности
                self.add_performance_metric(file_uuid, 'transcription_time', data['processing_time'])

                # Добавляем системные метрики для этой транскрипции
                self._add_transcription_system_metrics(file_uuid, data)

            return success

        except Exception as e:
            logger.error(f"Error recording transcription complete: {e}")
            return False

    def _add_transcription_system_metrics(self, data: Dict[str, Any]):
        """Добавление системных метрик для конкретной транскрипции"""
        try:
            import psutil

            # Собираем метрики во время транскрипции
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()

            system_metrics = [
                {
                    'metric_type': 'transcription_cpu_usage',
                    'metric_value': cpu_percent,
                    'service': 'transcription'
                },
                {
                    'metric_type': 'transcription_memory_usage',
                    'metric_value': memory.percent,
                    'service': 'transcription'
                },
                {
                    'metric_type': 'text_length',
                    'metric_value': data.get('text_length', 0),
                    'service': 'transcription'
                },
                {
                    'metric_type': 'processing_time',
                    'metric_value': data.get('processing_time', 0),
                    'service': 'transcription'
                }
            ]

            for metric in system_metrics:
                self.repository.add_system_metric(metric)

        except Exception as e:
            logger.error(f"Error adding transcription system metrics: {e}")

    def get_system_overview(self) -> Dict[str, Any]:
        """Полный обзор системы на реальных данных"""
        try:
            overview = {
                'daily_stats': self.get_daily_statistics(7),
                'language_distribution': self.get_language_distribution(),
                'success_rate': self.get_success_rate(7),
                'performance_metrics': self.get_performance_metrics(24),
                'system_metrics': self.get_system_metrics(24),
                'top_words': self.get_top_words(20, 30),
                'recent_transcriptions': self.get_recent_transcriptions(10),
                'total_transcriptions': self._get_total_count(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            return overview
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {'error': str(e)}

    def get_daily_statistics(self, days: int = 7):
        """Статистика за последние N дней"""
        try:
            return self.repository.get_daily_statistics(days)
        except Exception as e:
            logger.error(f"Error getting daily statistics: {e}")
            return []

    def get_language_distribution(self):
        """Распределение по языкам"""
        try:
            return self.repository.get_language_distribution()
        except Exception as e:
            logger.error(f"Error getting language distribution: {e}")
            return {}

    def get_success_rate(self, days: int = 7):
        """Процент успешных транскрипций"""
        try:
            return self.repository.get_success_rate(days)
        except Exception as e:
            logger.error(f"Error getting success rate: {e}")
            return {'success_rate': 0}

    def get_performance_metrics(self, hours: int = 24):
        """Метрики производительности"""
        try:
            return self.repository.get_performance_metrics(hours)
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    def get_system_metrics(self, hours: int = 24):
        """Системные метрики"""
        try:
            return self.repository.get_system_metrics(hours)
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}

    def get_top_words(self, limit: int = 20, min_length: int = 3):
        """Самые частые слова"""
        try:
            return self.repository.get_top_words(limit, min_length)
        except Exception as e:
            logger.error(f"Error getting top words: {e}")
            return []

    def get_recent_transcriptions(self, limit: int = 10):
        """Последние транскрипции"""
        try:
            return self.repository.get_recent_transcriptions(limit)
        except Exception as e:
            logger.error(f"Error getting recent transcriptions: {e}")
            return []

    def _get_total_count(self):
        """Общее количество транскрипций"""
        try:
            return self.repository.get_total_count()
        except Exception as e:
            logger.error(f"Error getting total count: {e}")
            return {'total': 0, 'completed': 0, 'failed': 0}

    def record_transcription_start(self, data: Dict[str, Any]) -> str:
        """Запись начала транскрипции"""
        try:
            return self.repository.create_transcription_record(data)
        except Exception as e:
            logger.error(f"Error recording transcription start: {e}")
            return ""

    def record_transcription_error(self, file_uuid: str, error_message: str) -> bool:
        """Запись ошибки транскрипции"""
        try:
            return self.repository.update_transcription_record(file_uuid, {
                'status': 'failed',
                'error_message': error_message,
                'completed_at': datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Error recording transcription error: {e}")
            return False

    def add_word_statistics(self, file_uuid: str, word_stats: list) -> bool:
        """Добавление статистики слов"""
        try:
            return self.repository.add_word_statistics(file_uuid, word_stats)
        except Exception as e:
            logger.error(f"Error adding word statistics: {e}")
            return False

    def add_performance_metric(self, file_uuid: str, metric_type: str, value: float) -> bool:
        """Добавление метрики производительности"""
        try:
            return self.repository.add_performance_metric(file_uuid, metric_type, value)
        except Exception as e:
            logger.error(f"Error adding performance metric: {e}")
            return False