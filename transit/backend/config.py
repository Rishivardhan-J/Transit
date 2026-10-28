from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://transit_user:transit_password@postgres:5432/transit_db"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "supersecretkey-for-local-dev-only-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    SENTRY_DSN: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    CELERY_EAGER: bool = False   # dev only: run jobs inline in the API process (no Redis/worker needed)
    STATION_CODE: str = "DLA3"   # Amazon station whose delivery area the leg model should assume
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
