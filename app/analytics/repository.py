from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Репозиторий для работы с аналитикой на реальных данных"""

    def __init__(self, db: Session):
        self.db = db

    def create_transcription_record(self, data: Dict[str, Any]) -> str:
        """Создание записи о начале транскрипции"""
        try:
            file_uuid = data.get('file_uuid') or data.get('transcription_id', '')

            query = text("""
                INSERT INTO transcription_records (
                    id, filename, file_size, duration, language,
                    transcription_id, file_uuid, status, created_at
                ) VALUES (
                    :id, :filename, :file_size, :duration, :language,
                    :transcription_id, :file_uuid, 'started', NOW()
                )
                RETURNING id
            """)

            params = {
                'id': file_uuid,
                'filename': data.get('filename', ''),
                'file_size': data.get('file_size', 0),
                'duration': data.get('duration', 0),
                'language': data.get('language', 'ru'),
                'transcription_id': data.get('transcription_id', ''),
                'file_uuid': file_uuid
            }

            result = self.db.execute(query, params)
            self.db.commit()

            record_id = result.fetchone()[0]
            return record_id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating transcription record: {e}")
            return ""

    def update_transcription_record(self, file_uuid: str, data: Dict[str, Any]) -> bool:
        """Обновление записи транскрипции"""
        try:
            # Собираем SET часть запроса
            set_parts = []
            params = {'file_uuid': file_uuid}

            for key, value in data.items():
                if key == 'completed_at' and isinstance(value, datetime):
                    params[key] = value
                elif key == 'completed_at' and value is None:
                    params[key] = datetime.now(timezone.utc)
                else:
                    params[key] = value
                set_parts.append(f"{key} = :{key}")

            set_clause = ", ".join(set_parts)

            query = text(f"""
                UPDATE transcription_records
                SET {set_clause}
                WHERE id = :file_uuid
            """)

            result = self.db.execute(query, params)
            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating transcription record: {e}")
            return False

    def get_total_count(self) -> Dict[str, int]:
        """Получение общего количества транскрипций"""
        try:
            query = text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM transcription_records
            """)

            result = self.db.execute(query).fetchone()

            if result:
                return {
                    'total': result[0] or 0,
                    'completed': result[1] or 0,
                    'failed': result[2] or 0
                }
            return {'total': 0, 'completed': 0, 'failed': 0}

        except Exception as e:
            logger.error(f"Error getting total count: {e}")
            return {'total': 0, 'completed': 0, 'failed': 0}

    def get_daily_statistics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Статистика за последние N дней"""
        try:
            query = text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM transcription_records
                WHERE created_at >= NOW() - INTERVAL ':days days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)

            result = self.db.execute(query, {'days': days})
            rows = result.fetchall()

            daily_stats = []
            for row in rows:
                daily_stats.append({
                    'date': row[0].strftime('%Y-%m-%d') if row[0] else '',
                    'total': row[1] or 0,
                    'completed': row[2] or 0,
                    'failed': row[3] or 0
                })

            return daily_stats

        except Exception as e:
            logger.error(f"Error getting daily statistics: {e}")
            return []

    def get_language_distribution(self) -> Dict[str, int]:
        """Распределение по языкам"""
        try:
            query = text("""
                SELECT 
                    COALESCE(language, 'unknown') as language,
                    COUNT(*) as count
                FROM transcription_records
                GROUP BY language
                ORDER BY count DESC
            """)

            result = self.db.execute(query)
            rows = result.fetchall()

            distribution = {}
            for row in rows:
                distribution[row[0]] = row[1] or 0

            return distribution

        except Exception as e:
            logger.error(f"Error getting language distribution: {e}")
            return {}

    def get_success_rate(self, days: int = 7) -> Dict[str, float]:
        """Процент успешных транскрипций"""
        try:
            query = text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM transcription_records
                WHERE created_at >= NOW() - INTERVAL ':days days'
            """)

            result = self.db.execute(query, {'days': days}).fetchone()

            total = result[0] or 0
            completed = result[1] or 0

            if total > 0:
                success_rate = (completed / total) * 100
            else:
                success_rate = 0.0

            return {'success_rate': round(success_rate, 1)}

        except Exception as e:
            logger.error(f"Error getting success rate: {e}")
            return {'success_rate': 0.0}

    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Метрики производительности"""
        try:
            # Среднее время обработки
            query_avg = text("""
                SELECT 
                    AVG(processing_time) as avg_processing_time,
                    MAX(processing_time) as max_processing_time
                FROM transcription_records
                WHERE status = 'completed' 
                AND processing_time > 0
                AND created_at >= NOW() - INTERVAL ':hours hours'
            """)

            result = self.db.execute(query_avg, {'hours': hours}).fetchone()

            avg_time = result[0] or 0
            max_time = result[1] or 0

            # Статистика по длине текста
            query_text = text("""
                SELECT 
                    AVG(text_length) as avg_text_length,
                    MAX(text_length) as max_text_length
                FROM transcription_records
                WHERE status = 'completed' 
                AND text_length > 0
                AND created_at >= NOW() - INTERVAL ':hours hours'
            """)

            result_text = self.db.execute(query_text, {'hours': hours}).fetchone()

            return {
                'avg_processing_time': round(float(avg_time), 2),
                'max_processing_time': round(float(max_time), 2),
                'avg_text_length': round(float(result_text[0] or 0), 0),
                'max_text_length': round(float(result_text[1] or 0), 0)
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'avg_processing_time': 0, 'max_processing_time': 0}

    def get_system_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Системные метрики (последние)"""
        try:
            query = text("""
                SELECT 
                    metric_type,
                    AVG(metric_value) as avg_value,
                    MAX(metric_value) as max_value,
                    MIN(metric_value) as min_value
                FROM system_metrics
                WHERE timestamp >= NOW() - INTERVAL ':hours hours'
                GROUP BY metric_type
            """)

            result = self.db.execute(query, {'hours': hours})
            rows = result.fetchall()

            metrics = {}
            for row in rows:
                metric_type = row[0]
                metrics[metric_type] = {
                    'avg': round(float(row[1] or 0), 1),
                    'max': round(float(row[2] or 0), 1),
                    'min': round(float(row[3] or 0), 1)
                }

            # Добавляем текущие метрики системы
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()

                metrics['current_cpu'] = round(cpu_percent, 1)
                metrics['current_memory'] = round(memory.percent, 1)
                metrics['memory_available_mb'] = round(memory.available / (1024 * 1024), 0)
            except ImportError:
                logger.warning("psutil not available for system metrics")

            return metrics

        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}

    def get_top_words(self, limit: int = 20, min_length: int = 3) -> List[Dict[str, Any]]:
        """Самые частые слова"""
        try:
            query = text("""
                SELECT 
                    word,
                    SUM(count) as total_count
                FROM word_statistics
                WHERE LENGTH(word) >= :min_length
                GROUP BY word
                ORDER BY total_count DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {'min_length': min_length, 'limit': limit})
            rows = result.fetchall()

            top_words = []
            for row in rows:
                top_words.append({
                    'word': row[0],
                    'count': row[1] or 0
                })

            return top_words

        except Exception as e:
            logger.error(f"Error getting top words: {e}")
            return []

    def get_recent_transcriptions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Последние транскрипции"""
        try:
            query = text("""
                SELECT 
                    id,
                    filename,
                    language,
                    status,
                    text_length,
                    processing_time,
                    created_at
                FROM transcription_records
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {'limit': limit})
            rows = result.fetchall()

            transcriptions = []
            for row in rows:
                transcriptions.append({
                    'id': row[0],
                    'filename': row[1],
                    'language': row[2],
                    'status': row[3],
                    'text_length': row[4] or 0,
                    'processing_time': row[5] or 0,
                    'created_at': row[6].isoformat() if row[6] else ''
                })

            return transcriptions

        except Exception as e:
            logger.error(f"Error getting recent transcriptions: {e}")
            return []

    def add_system_metric(self, metric_data: Dict[str, Any]) -> bool:
        """Добавление системной метрики"""
        try:
            query = text("""
                INSERT INTO system_metrics (
                    timestamp, metric_type, metric_value, service
                ) VALUES (
                    NOW(), :metric_type, :metric_value, :service
                )
            """)

            params = {
                'metric_type': metric_data['metric_type'],
                'metric_value': metric_data['metric_value'],
                'service': metric_data.get('service', 'transcription')
            }

            self.db.execute(query, params)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding system metric: {e}")
            return False

    def add_word_statistics(self, file_uuid: str, word_stats: list) -> bool:
        """Добавление статистики слов"""
        try:
            for word_stat in word_stats:
                query = text("""
                    INSERT INTO word_statistics (
                        file_uuid, word, count, language, created_at
                    ) VALUES (
                        :file_uuid, :word, :count, :language, NOW()
                    )
                """)

                params = {
                    'file_uuid': file_uuid,
                    'word': word_stat['word'],
                    'count': word_stat['count'],
                    'language': word_stat.get('language', 'unknown')
                }

                self.db.execute(query, params)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding word statistics: {e}")
            return False

    def add_performance_metric(self, file_uuid: str, metric_type: str, value: float) -> bool:
        """Добавление метрики производительности"""
        try:
            query = text("""
                INSERT INTO performance_metrics (
                    file_uuid, metric_name, metric_value, created_at
                ) VALUES (
                    :file_uuid, :metric_name, :metric_value, NOW()
                )
            """)

            params = {
                'file_uuid': file_uuid,
                'metric_name': metric_type,
                'metric_value': value
            }

            self.db.execute(query, params)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding performance metric: {e}")
            return False

    def record_transcription_error(self, file_uuid: str, error_message: str) -> bool:
        """Запись ошибки транскрипции"""
        try:
            query = text("""
                UPDATE transcription_records 
                SET status = 'failed',
                    error_message = :error_message,
                    completed_at = NOW()
                WHERE id = :file_uuid
            """)

            params = {
                'file_uuid': file_uuid,
                'error_message': error_message
            }

            result = self.db.execute(query, params)
            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording transcription error: {e}")
            return False