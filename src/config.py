"""
Configuration system for Marketing Automation MCP
Handles platform-specific configurations and secrets
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from cryptography.fernet import Fernet

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PlatformConfig:
    """Configuration for a marketing platform"""

    enabled: bool = False
    credentials: Dict[str, Any] = field(default_factory=dict)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1


@dataclass
class GoogleAdsConfig(PlatformConfig):
    """Google Ads specific configuration"""

    developer_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    customer_id: str = ""
    login_customer_id: Optional[str] = None

    def __post_init__(self):
        self.rate_limits = {"requests_per_second": 10, "requests_per_day": 15000}


@dataclass
class FacebookAdsConfig(PlatformConfig):
    """Facebook Ads specific configuration"""

    app_id: str = ""
    app_secret: str = ""
    access_token: str = ""
    ad_account_id: str = ""

    def __post_init__(self):
        self.rate_limits = {"requests_per_hour": 200, "requests_per_day": 10000}


@dataclass
class GoogleAnalyticsConfig(PlatformConfig):
    """Google Analytics specific configuration"""

    property_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    service_account_path: Optional[str] = None

    def __post_init__(self):
        self.rate_limits = {"requests_per_hour": 100, "requests_per_day": 5000}


@dataclass
class LLMConfig:
    """Generic LLM provider configuration (supports OpenAI, Dify, Local, etc.)"""

    provider: str = "OPENAI"  # Options: OPENAI, DIFY, LOCAL
    # Dify (self-hosted) settings
    dify_api_url: str = ""
    dify_api_key: str = ""
    dify_model: str = ""
    # Local model settings (optional)
    local_model_path: str = ""
    timeout: int = 60


@dataclass
class OpenAIConfig:
    """OpenAI configuration"""

    api_key: str = ""
    model: str = "gpt-4-turbo-preview"
    max_tokens: int = 4000
    temperature: float = 0.7
    timeout: int = 60


@dataclass
class DatabaseConfig:
    """Database configuration"""

    url: str = "sqlite:///marketing_automation.db"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class SecurityConfig:
    """Security configuration"""

    secret_key: str = ""
    encryption_key: str = ""
    api_key_encryption: bool = True
    audit_logging: bool = True
    allowed_origins: list = field(default_factory=lambda: ["*"])
    secure_headers: bool = True


@dataclass
class PerformanceConfig:
    """Performance configuration"""

    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    batch_size: int = 100
    concurrent_requests: int = 5
    request_timeout: int = 30
    slow_query_threshold: float = 1.0  # seconds


@dataclass
class LoggingConfig:
    """Logging configuration"""

    level: str = "INFO"
    format: str = "json"
    file: Optional[str] = "logs/marketing_automation.log"
    max_size: int = 10485760  # 10MB
    backup_count: int = 5
    structured: bool = True


class Config:
    """Main configuration class"""

    def __init__(self):
        self.google_ads = GoogleAdsConfig()
        self.facebook_ads = FacebookAdsConfig()
        self.google_analytics = GoogleAnalyticsConfig()
        self.openai = OpenAIConfig()
        # Generic LLM provider config (supports Dify, Local, etc.)
        self.llm = LLMConfig()
        self.database = DatabaseConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        self.logging = LoggingConfig()

        # Platform registry
        self.platforms = {
            "google_ads": self.google_ads,
            "facebook_ads": self.facebook_ads,
            "google_analytics": self.google_analytics,
        }

        # Encryption for sensitive data
        self._cipher_suite = None
        if self.security.api_key_encryption:
            self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption for sensitive data"""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key()
            logger.warning("No encryption key found, generating new one")
        self._cipher_suite = Fernet(key if isinstance(key, bytes) else key.encode())

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from file and environment"""
        config = cls()

        # Load from file if provided
        if config_path and Path(config_path).exists():
            logger.info(f"Loading config from {config_path}")
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
                config._update_from_dict(data)

        # Override with environment variables
        config._load_from_env()

        # Validate configuration
        config._validate()

        logger.info("Configuration loaded successfully")
        return config

    def _update_from_dict(self, data: Dict[str, Any]):
        """Update configuration from dictionary"""
        if "google_ads" in data:
            self._update_platform(self.google_ads, data["google_ads"])
        if "facebook_ads" in data:
            self._update_platform(self.facebook_ads, data["facebook_ads"])
        if "google_analytics" in data:
            self._update_platform(self.google_analytics, data["google_analytics"])
        if "openai" in data:
            self._update_dataclass(self.openai, data["openai"])
        if "database" in data:
            self._update_dataclass(self.database, data["database"])
        if "security" in data:
            self._update_dataclass(self.security, data["security"])
        if "performance" in data:
            self._update_dataclass(self.performance, data["performance"])
        if "logging" in data:
            self._update_dataclass(self.logging, data["logging"])

    def _update_platform(self, platform: PlatformConfig, data: Dict[str, Any]):
        """Update platform configuration"""
        for key, value in data.items():
            if hasattr(platform, key):
                setattr(platform, key, value)
        platform.enabled = bool(data.get("enabled", False))

    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """Update dataclass from dictionary"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Google Ads
        self.google_ads.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        self.google_ads.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.google_ads.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.google_ads.refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
        self.google_ads.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        self.google_ads.enabled = bool(self.google_ads.developer_token)

        # Facebook Ads
        self.facebook_ads.app_id = os.getenv("FACEBOOK_APP_ID", "")
        self.facebook_ads.app_secret = os.getenv("FACEBOOK_APP_SECRET", "")
        self.facebook_ads.access_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
        self.facebook_ads.ad_account_id = os.getenv("FACEBOOK_AD_ACCOUNT_ID", "")
        self.facebook_ads.enabled = bool(self.facebook_ads.app_id)

        # Google Analytics
        self.google_analytics.property_id = os.getenv(
            "GOOGLE_ANALYTICS_PROPERTY_ID", ""
        )
        self.google_analytics.client_id = os.getenv("GOOGLE_ANALYTICS_CLIENT_ID", "")
        self.google_analytics.client_secret = os.getenv(
            "GOOGLE_ANALYTICS_CLIENT_SECRET", ""
        )
        self.google_analytics.refresh_token = os.getenv(
            "GOOGLE_ANALYTICS_REFRESH_TOKEN", ""
        )
        self.google_analytics.enabled = bool(self.google_analytics.property_id)

        # OpenAI / LLM provider settings
        # LLM provider selection
        self.llm.provider = os.getenv("LLM_PROVIDER", self.llm.provider).upper()
        # OpenAI-specific settings
        self.openai.api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai.model = os.getenv("OPENAI_MODEL", self.openai.model)
        # Dify (self-hosted) settings
        self.llm.dify_api_url = os.getenv("DIFY_API_URL", self.llm.dify_api_url)
        self.llm.dify_api_key = os.getenv("DIFY_API_KEY", self.llm.dify_api_key)
        self.llm.dify_model = os.getenv("DIFY_MODEL", self.llm.dify_model)
        # Local model settings (optional)
        self.llm.local_model_path = os.getenv(
            "LOCAL_MODEL_PATH", self.llm.local_model_path
        )

        # Database
        self.database.url = os.getenv("DATABASE_URL", self.database.url)

        # Security
        self.security.secret_key = os.getenv("SECRET_KEY", "")
        self.security.encryption_key = os.getenv("ENCRYPTION_KEY", "")

        # Logging
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)

    def _validate(self):
        """Validate configuration"""
        errors = []

        # Check required LLM provider credentials
        if self.llm.provider == "OPENAI":
            if not self.openai.api_key:
                errors.append("OpenAI API key is required when LLM_PROVIDER=OPENAI")
        elif self.llm.provider == "DIFY":
            # For Dify, require both URL and API key
            if not (self.llm.dify_api_url and self.llm.dify_api_key):
                errors.append(
                    "Dify API URL and API key are required when LLM_PROVIDER=DIFY"
                )
        # LOCAL provider generally requires no external API keys; allow further validation in runtime adapters

        # Check at least one platform is configured
        if not any(p.enabled for p in self.platforms.values()):
            logger.warning("No marketing platforms configured")

        # Check security keys
        if not self.security.secret_key:
            self.security.secret_key = os.urandom(32).hex()
            logger.warning("Generated random secret key")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

    def encrypt_value(self, value: str) -> str:
        """Encrypt a sensitive value"""
        if not self._cipher_suite:
            return value
        return self._cipher_suite.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a sensitive value"""
        if not self._cipher_suite:
            return encrypted_value
        return self._cipher_suite.decrypt(encrypted_value.encode()).decode()

    def get_platform_config(self, platform: str) -> Optional[PlatformConfig]:
        """Get configuration for a specific platform"""
        return self.platforms.get(platform.lower())

    def has_platform_credentials(self, platform: Any) -> bool:
        """Check if platform has credentials configured"""
        platform_name = platform.value if hasattr(platform, "value") else str(platform)
        config = self.get_platform_config(platform_name.lower().replace("_", ""))

        if not config:
            return False

        if isinstance(config, GoogleAdsConfig):
            return bool(config.developer_token and config.client_id)
        elif isinstance(config, FacebookAdsConfig):
            return bool(config.app_id and config.access_token)
        elif isinstance(config, GoogleAnalyticsConfig):
            return bool(
                config.property_id and (config.client_id or config.service_account_path)
            )

        return False

    def save(self, config_path: str):
        """Save configuration to file (excluding sensitive data)"""
        data = {
            "google_ads": {
                "enabled": self.google_ads.enabled,
                "rate_limits": self.google_ads.rate_limits,
                "timeout": self.google_ads.timeout,
            },
            "facebook_ads": {
                "enabled": self.facebook_ads.enabled,
                "rate_limits": self.facebook_ads.rate_limits,
                "timeout": self.facebook_ads.timeout,
            },
            "google_analytics": {
                "enabled": self.google_analytics.enabled,
                "rate_limits": self.google_analytics.rate_limits,
                "timeout": self.google_analytics.timeout,
            },
            "openai": {
                "model": self.openai.model,
                "max_tokens": self.openai.max_tokens,
                "temperature": self.openai.temperature,
            },
            "database": {
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow,
            },
            "performance": {
                "cache_enabled": self.performance.cache_enabled,
                "cache_ttl": self.performance.cache_ttl,
                "batch_size": self.performance.batch_size,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "structured": self.logging.structured,
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        logger.info(f"Configuration saved to {config_path}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for debugging)"""
        return {
            "platforms_enabled": [p for p, c in self.platforms.items() if c.enabled],
            "llm_provider": self.llm.provider,
            "openai_model": self.openai.model,
            "database_url": self.database.url.split("@")[0]
            if "@" in self.database.url
            else self.database.url,
            "cache_enabled": self.performance.cache_enabled,
            "log_level": self.logging.level,
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def set_config(config: Config):
    """Set global configuration instance"""
    global _config
    _config = config
