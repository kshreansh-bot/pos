"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: supermarket_billing_system
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Database directory and file
DATABASE_DIR = PROJECT_ROOT / "backend" / "instance"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "supermarket.db"


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Supermarket POS & Inventory System"
    debug: bool = False
    environment: str = "production"

    # Security
    secret_key: str = "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Database
    database_url: str = (
        f"sqlite+aiosqlite:///{DATABASE_PATH.as_posix()}"
    )

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Business Rules
    days_to_expiry_warning: int = 7
    default_cashier_discount_limit: int = 10
    default_tax_rate: int = 18

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()