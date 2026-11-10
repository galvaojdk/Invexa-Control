from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Invexa Control"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./control.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
