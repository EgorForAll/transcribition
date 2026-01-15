import redis
from typing import Optional
import json
from app.config import settings
import time

class RedisClient:
    """Клиент для работы с Redis"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        """Подключение к Redis"""
        try:
            print(f"🔴 [Redis] Checking connection...")
            print(f"🔴 [Redis] Enabled: {settings.REDIS_ENABLED}")

            # Если Redis отключен, выходим
            if not settings.REDIS_ENABLED:
                print("🔴 [Redis] Disabled in settings, skipping connection")
                return

            print(f"🔴 [Redis] Attempting to connect to {settings.REDIS_HOST}:{settings.REDIS_PORT}...")

            connection_params = {
                'host': settings.REDIS_HOST,
                'port': settings.REDIS_PORT,
                'db': settings.REDIS_DB,
                'decode_responses': True,
                'socket_connect_timeout': 3,
                'socket_timeout': 3,
                'retry_on_timeout': True
            }

            # Добавляем пароль только если он указан
            if settings.REDIS_PASSWORD:
                connection_params['password'] = settings.REDIS_PASSWORD
                print(f"🔴 [Redis] Using password authentication")

            self.redis_client = redis.Redis(**connection_params)

            # Тестируем подключение
            start_time = time.time()
            response = self.redis_client.ping()
            elapsed = time.time() - start_time

            if response:
                print(f"✅ [Redis] Connected successfully! Ping: {elapsed:.2f}s")
                # Выводим базовую информацию
                try:
                    info = self.redis_client.info('server')
                    print(f"✅ [Redis] Version: {info.get('redis_version')}")
                    print(f"✅ [Redis] Mode: {info.get('redis_mode')}")
                except:
                    pass
            else:
                print(f"❌ [Redis] Ping failed")
                self.redis_client = None

        except redis.ConnectionError as e:
            print(f"❌ [Redis] Connection error: {e}")
            print(f"   Trying host: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            self.redis_client = None
        except redis.AuthenticationError as e:
            print(f"❌ [Redis] Authentication failed: {e}")
            self.redis_client = None
        except Exception as e:
            print(f"❌ [Redis] Unexpected error: {type(e).__name__}: {e}")
            self.redis_client = None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Сохранение значения в Redis"""
        if not self.redis_client:
            return False

        try:
            if ttl:
                self.redis_client.setex(key, ttl, value)
            else:
                self.redis_client.set(key, value)
            return True
        except Exception as e:
            print(f"❌ Redis set error: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """Получение значения из Redis"""
        if not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            return value if value else None
        except Exception as e:
            print(f"❌ Redis get error: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Удаление ключа из Redis"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"❌ Redis delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        if not self.redis_client:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"❌ Redis exists error: {e}")
            return False

    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """Сохранение JSON в Redis"""
        try:
            json_value = json.dumps(value)
            return self.set(key, json_value, ttl)
        except Exception as e:
            print(f"❌ Redis set_json error: {e}")
            return False

    def get_json(self, key: str) -> Optional[dict]:
        """Получение JSON из Redis"""
        try:
            value = self.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"❌ Redis get_json error: {e}")
            return None

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Инкремент значения"""
        if not self.redis_client:
            return None

        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"❌ Redis increment error: {e}")
            return None

    def cache_transcription(self, file_id: str, transcription_text: str, ttl: int = 3600) -> bool:
        """Кэширование транскрипции"""
        return self.set(f"transcription:{file_id}", transcription_text, ttl)

    def get_cached_transcription(self, file_id: str) -> Optional[str]:
        """Получение транскрипции из кэша"""
        return self.get(f"transcription:{file_id}")

    def cache_file_info(self, file_id: str, info: dict, ttl: int = 3600) -> bool:
        """Кэширование информации о файле"""
        return self.set_json(f"file_info:{file_id}", info, ttl)

    def get_cached_file_info(self, file_id: str) -> Optional[dict]:
        """Получение информации о файле из кэша"""
        return self.get_json(f"file_info:{file_id}")


redis_client = RedisClient()
