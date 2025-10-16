# File: config/settings.py
"""
Configuration Settings

FIXED: Added wandb_mode field to support WANDB_MODE=disabled
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # API Keys
    xai_api_key: str
    openai_api_key: str
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    together_api_key: Optional[str] = Field(None, env="TOGETHER_API_KEY")
    
    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "cop_pipeline"
    postgres_user: str = "cop_user"
    postgres_password: str
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # Monitoring
    wandb_api_key: Optional[str] = None
    wandb_project: str = "cop-red-teaming"
    wandb_mode: Optional[str] = None  # NEW: Support WANDB_MODE=disabled
    prometheus_port: int = 9090
    
    # Pipeline Configuration
    max_iterations: int = 10
    jailbreak_threshold: float = 10.0
    similarity_threshold: float = 1.0
    default_red_teaming_agent: str = "grok-2"
    default_judge_llm: str = "gpt-4o"
    
    # Rate Limiting
    max_concurrent_requests: int = 10
    rate_limit_per_minute: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # NEW: Ignore extra fields in .env
    
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"
    
    @property
    def is_wandb_enabled(self) -> bool:
        """Check if W&B is enabled based on mode and API key."""
        if self.wandb_mode and self.wandb_mode.lower() == "disabled":
            return False
        if not self.wandb_api_key or self.wandb_api_key.strip() == "":
            return False
        if self.wandb_api_key == "your_wandb_key":
            return False
        return True


@lru_cache()
def get_settings() -> Settings:
    return Settings()