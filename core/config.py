"""Configuration module using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram Bot
    BOT_TOKEN: str
    ADMIN_TG_ID: int
    
    # 3x-ui API
    XUI_BASE_URL: str  # Example: https://your-server.com
    XUI_USERNAME: str
    XUI_PASSWORD: str
    XUI_VERIFY_SSL: bool = False  # Проверка SSL сертификатов (False для самоподписанных)
    XUI_EXTERNAL_ADDRESS: str = ""  # Внешний адрес сервера для клиентских подключений (например: example.com)
    XUI_EXTERNAL_PORT: int = 443  # Внешний порт для клиентских подключений (по умолчанию 443)
    
    # VLESS Connection (fallback settings, optional)
    # Эти настройки используются только если не удается получить ссылку из API
    VLESS_SERVER: str = ""  # Server IP or domain
    VLESS_PORT: int = 443  # Server port
    VLESS_SNI: str = ""  # Server Name Indication (domain)
    VLESS_SECURITY: str = "tls"  # Security type
    VLESS_TYPE: str = "tcp"  # Connection type
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/vpn_bot.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"
    LOG_ROTATION: str = "00:00"  # Rotate at midnight
    LOG_RETENTION: str = "30 days"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
