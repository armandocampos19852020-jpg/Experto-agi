"""
Production configuration for Experto-agi API
"""
import os
from datetime import timedelta

# ==================== SERVER ====================
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
WORKERS = int(os.environ.get("WORKERS", 4))
RELOAD = os.environ.get("RELOAD", "false").lower() == "true"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")

# ==================== DATABASE ====================
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/experto_agi"
)
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", 20))
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", 30))

# ==================== CACHE ====================
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
CACHE_TTL = int(os.environ.get("CACHE_TTL", 3600))

# ==================== RATE LIMITING ====================
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", 100))
RATE_LIMIT_PERIOD = int(os.environ.get("RATE_LIMIT_PERIOD", 60))

# ==================== CORS ====================
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "*"
).split(",")

# ==================== API KEYS ====================
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ==================== MONITORING ====================
PROMETHEUS_ENABLED = os.environ.get("PROMETHEUS_ENABLED", "true").lower() == "true"
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
LOG_PATH = os.environ.get("LOG_PATH", "logs")

# ==================== PERFORMANCE ====================
GZIP_ENABLED = os.environ.get("GZIP_ENABLED", "true").lower() == "true"
GZIP_MIN_SIZE = int(os.environ.get("GZIP_MIN_SIZE", 1000))
KEEP_ALIVE_TIMEOUT = int(os.environ.get("KEEP_ALIVE_TIMEOUT", 5))

# ==================== TIMEOUTS ====================
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 300))
CODE_GENERATION_TIMEOUT = int(os.environ.get("CODE_GENERATION_TIMEOUT", 120))

# ==================== LIMITS ====================
MAX_BODY_SIZE = int(os.environ.get("MAX_BODY_SIZE", 104857600))  # 100MB
MAX_CONCURRENT_REQUESTS = int(os.environ.get("MAX_CONCURRENT_REQUESTS", 100))
