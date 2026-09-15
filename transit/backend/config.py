from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://transit_user:transit_password@postgres:5432/transit_db"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "supersecretkey-for-local-dev-only-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    SENTRY_DSN: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
