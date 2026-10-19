"""
Application configuration management for LEXLY Backend using Pydantic Settings.
"""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables or .env file.
    """
    PROJECT_NAME: str = "LEXLY Backend"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    # External APIs
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Database connection pool settings
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    DB_POOL_TIMEOUT: float = 30.0

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Ensures DATABASE_URL begins with postgresql:// or postgresql+asyncpg://
        and converts it to standard postgresql:// for asyncpg driver compatibility.
        """
        if not v:
            raise ValueError("DATABASE_URL must not be empty.")
        
        # asyncpg natively expects postgresql:// or postgres://
        if v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql+asyncpg://", "postgresql://", 1)
        if not (v.startswith("postgresql://") or v.startswith("postgres://")):
            raise ValueError("DATABASE_URL must start with postgresql:// or postgres://")
        return v

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
