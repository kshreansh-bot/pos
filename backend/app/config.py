"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Supermarket POS & Inventory System"
    debug: bool = False
    environment: str = "production"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Database
    database_url: str = "sqlite+aiosqlite:///./supermarket.db"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Business Rules
    days_to_expiry_warning: int = 7
    default_cashier_discount_limit: int = 10
    default_tax_rate: int = 18

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
