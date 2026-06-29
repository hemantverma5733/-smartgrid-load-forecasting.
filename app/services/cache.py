import json
import logging
import redis
from app.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.enabled = False
        self._local_cache = {}
        
        try:
            # Parse Redis URL or fallback
            self.client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Ping redis to test connection
            self.client.ping()
            self.enabled = True
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Redis connection failed ({e}). Falling back to in-memory cache.")
            self.client = None

    def get(self, key: str):
        if self.enabled:
            try:
                data = self.client.get(key)
                return json.loads(data) if data else None
            except Exception as e:
                logger.error(f"Redis GET failed for key {key}: {e}")
                
        # In-memory fallback
        return self._local_cache.get(key)

    def set(self, key: str, value, expire_seconds: int = 3600):
        if self.enabled:
            try:
                self.client.set(key, json.dumps(value), ex=expire_seconds)
                return True
            except Exception as e:
                logger.error(f"Redis SET failed for key {key}: {e}")
                
        # In-memory fallback
        self._local_cache[key] = value
        # Simple local cleanup could be added, but in-memory is mainly for dev fallback
        return True

    def delete(self, key: str):
        if self.enabled:
            try:
                self.client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis DELETE failed for key {key}: {e}")
                
        if key in self._local_cache:
            del self._local_cache[key]
        return True

cache_service = CacheService()
