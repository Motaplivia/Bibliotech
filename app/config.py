from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Original variable names
    DATABASE_PORT: int
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_HOSTNAME: str
    
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.DATABASE_PORT}/"
            f"{self.POSTGRES_DB}"
        )
    
    # Allow additional fields from environment variables
    class Config:
        env_file = './.env'
        extra = 'ignore'  # This will ignore extra fields instead of raising an error

settings = Settings()