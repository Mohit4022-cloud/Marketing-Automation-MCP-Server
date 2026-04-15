"""
Configuration system for Marketing Automation MCP.
Handles platform credentials, AI provider selection, and demo/live execution mode.
"""

from __future__ import annotations

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
    """Configuration for a marketing platform."""

    enabled: bool = False
    credentials: Dict[str, Any] = field(default_factory=dict)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1


@dataclass
class GoogleAdsConfig(PlatformConfig):
    """Google Ads specific configuration."""

    developer_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    customer_id: str = ""
    login_customer_id: Optional[str] = None

    def __post_init__(self):
        self.rate_limits = {
            "requests_per_second": 10,
            "requests_per_day": 15000,
        }


@dataclass
class FacebookAdsConfig(PlatformConfig):
    """Facebook Ads specific configuration."""

    app_id: str = ""
    app_secret: str = ""
    access_token: str = ""
    ad_account_id: str = ""

    def __post_init__(self):
        self.rate_limits = {
            "requests_per_hour": 200,
            "requests_per_day": 10000,
        }


@dataclass
class GoogleAnalyticsConfig(PlatformConfig):
    """Google Analytics specific configuration."""

    property_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    service_account_path: Optional[str] = None

    def __post_init__(self):
        self.rate_limits = {
            "requests_per_hour": 100,
            "requests_per_day": 5000,
        }


@dataclass
class ProviderConfig:
    """Base configuration for an AI provider."""

    api_key: str = ""
    model: str = ""
    max_tokens: int = 4000
    temperature: float = 0.2
    timeout: int = 60

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)


@dataclass
class OpenAIProviderConfig(ProviderConfig):
    """OpenAI configuration."""

    model: str = "gpt-5.4"


@dataclass
class AnthropicProviderConfig(ProviderConfig):
    """Anthropic configuration."""

    model: str = ""


@dataclass
class GeminiProviderConfig(ProviderConfig):
    """Gemini configuration."""

    model: str = ""


@dataclass
class AIConfig:
    """Top-level AI configuration."""

    provider: str = "openai"
    demo_mode: bool = False
    openai: OpenAIProviderConfig = field(default_factory=OpenAIProviderConfig)
    anthropic: AnthropicProviderConfig = field(default_factory=AnthropicProviderConfig)
    gemini: GeminiProviderConfig = field(default_factory=GeminiProviderConfig)

    def get_provider_config(
        self, provider_name: Optional[str] = None
    ) -> ProviderConfig:
        provider = (provider_name or self.provider).lower()
        config = getattr(self, provider, None)
        if not isinstance(config, ProviderConfig):
            raise ValueError(f"Unsupported AI provider '{provider}'")
        return config


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str = "sqlite:///marketing_automation.db"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class SecurityConfig:
    """Security configuration."""

    secret_key: str = ""
    encryption_key: str = ""
    api_key_encryption: bool = True
    audit_logging: bool = True
    allowed_origins: list = field(default_factory=lambda: ["*"])
    secure_headers: bool = True


@dataclass
class PerformanceConfig:
    """Performance configuration."""

    cache_enabled: bool = True
    cache_ttl: int = 3600
    batch_size: int = 100
    concurrent_requests: int = 5
    request_timeout: int = 30
    slow_query_threshold: float = 1.0


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    file: Optional[str] = "logs/marketing_automation.log"
    max_size: int = 10_485_760
    backup_count: int = 5
    structured: bool = True


class Config:
    """Main configuration object."""

    def __init__(self):
        self.google_ads = GoogleAdsConfig()
        self.facebook_ads = FacebookAdsConfig()
        self.google_analytics = GoogleAnalyticsConfig()
        self.ai = AIConfig()
        self.openai = self.ai.openai  # Backward-compatible alias.
        self.database = DatabaseConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        self.logging = LoggingConfig()

        self.platforms = {
            "google_ads": self.google_ads,
            "facebook_ads": self.facebook_ads,
            "google_analytics": self.google_analytics,
        }

        self._cipher_suite: Optional[Fernet] = None

    def _init_encryption(self):
        """Initialize encryption for sensitive data."""
        if not self.security.api_key_encryption:
            self._cipher_suite = None
            return

        key = self.security.encryption_key or os.getenv("ENCRYPTION_KEY")
        if not key:
            self.security.api_key_encryption = False
            self._cipher_suite = None
            logger.warning(
                "No ENCRYPTION_KEY configured; API key encryption is disabled for this process"
            )
            return
        self.security.encryption_key = key
        self._cipher_suite = Fernet(key.encode())

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from file and environment."""
        config = cls()

        if config_path and Path(config_path).exists():
            logger.info(f"Loading config from {config_path}")
            with open(config_path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            config._update_from_dict(data)

        config._load_from_env()
        config._init_encryption()
        config._validate()

        logger.info("Configuration loaded successfully")
        return config

    def _update_from_dict(self, data: Dict[str, Any]):
        """Update configuration from a dictionary."""
        if "google_ads" in data:
            self._update_platform(self.google_ads, data["google_ads"])
        if "facebook_ads" in data:
            self._update_platform(self.facebook_ads, data["facebook_ads"])
        if "google_analytics" in data:
            self._update_platform(self.google_analytics, data["google_analytics"])
        if "ai" in data:
            self._update_ai(self.ai, data["ai"])
        if "openai" in data:
            logger.warning(
                "Config section 'openai' is deprecated; use 'ai.openai' instead"
            )
            self._update_dataclass(self.ai.openai, data["openai"])
        if "database" in data:
            self._update_dataclass(self.database, data["database"])
        if "security" in data:
            self._update_dataclass(self.security, data["security"])
        if "performance" in data:
            self._update_dataclass(self.performance, data["performance"])
        if "logging" in data:
            self._update_dataclass(self.logging, data["logging"])

    def _update_ai(self, ai_config: AIConfig, data: Dict[str, Any]):
        """Update AI configuration from dictionary data."""
        scalar_fields = {"provider", "demo_mode"}
        for key in scalar_fields:
            if key in data:
                setattr(ai_config, key, data[key])

        for provider_name in ("openai", "anthropic", "gemini"):
            provider_data = data.get(provider_name)
            if provider_data:
                self._update_dataclass(getattr(ai_config, provider_name), provider_data)

    def _update_platform(self, platform: PlatformConfig, data: Dict[str, Any]):
        """Update platform configuration."""
        for key, value in data.items():
            if hasattr(platform, key):
                setattr(platform, key, value)
        platform.enabled = bool(data.get("enabled", False))

    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """Update a dataclass-style object from dictionary data."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def _load_from_env(self):
        """Load configuration from environment variables."""
        self.google_ads.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        self.google_ads.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.google_ads.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.google_ads.refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
        self.google_ads.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        self.google_ads.login_customer_id = os.getenv(
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID", self.google_ads.customer_id
        )
        self.google_ads.enabled = bool(self.google_ads.developer_token)

        self.facebook_ads.app_id = os.getenv("FACEBOOK_APP_ID", "")
        self.facebook_ads.app_secret = os.getenv("FACEBOOK_APP_SECRET", "")
        self.facebook_ads.access_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
        self.facebook_ads.ad_account_id = os.getenv("FACEBOOK_AD_ACCOUNT_ID", "")
        self.facebook_ads.enabled = bool(self.facebook_ads.app_id)

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
        self.google_analytics.service_account_path = (
            os.getenv("GOOGLE_ANALYTICS_SERVICE_ACCOUNT_PATH", "") or None
        )
        self.google_analytics.enabled = bool(self.google_analytics.property_id)

        self.ai.provider = os.getenv("AI_PROVIDER", self.ai.provider).lower()
        self.ai.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

        self.ai.openai.api_key = os.getenv("OPENAI_API_KEY", "")
        legacy_openai_model = os.getenv("OPENAI_MODEL")
        if legacy_openai_model:
            logger.warning("OPENAI_MODEL is deprecated; prefer AI_OPENAI_MODEL")
        self.ai.openai.model = os.getenv(
            "AI_OPENAI_MODEL", legacy_openai_model or self.ai.openai.model
        )
        self.ai.openai.max_tokens = int(
            os.getenv("AI_OPENAI_MAX_TOKENS", str(self.ai.openai.max_tokens))
        )
        self.ai.openai.temperature = float(
            os.getenv("AI_OPENAI_TEMPERATURE", str(self.ai.openai.temperature))
        )

        self.ai.anthropic.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.ai.anthropic.model = os.getenv("ANTHROPIC_MODEL", self.ai.anthropic.model)
        self.ai.anthropic.max_tokens = int(
            os.getenv("AI_ANTHROPIC_MAX_TOKENS", str(self.ai.anthropic.max_tokens))
        )
        self.ai.anthropic.temperature = float(
            os.getenv("AI_ANTHROPIC_TEMPERATURE", str(self.ai.anthropic.temperature))
        )

        self.ai.gemini.api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv(
            "GOOGLE_API_KEY", ""
        )
        self.ai.gemini.model = os.getenv("GEMINI_MODEL", self.ai.gemini.model)
        self.ai.gemini.max_tokens = int(
            os.getenv("AI_GEMINI_MAX_TOKENS", str(self.ai.gemini.max_tokens))
        )
        self.ai.gemini.temperature = float(
            os.getenv("AI_GEMINI_TEMPERATURE", str(self.ai.gemini.temperature))
        )

        self.database.url = os.getenv("DATABASE_URL", self.database.url)

        self.security.secret_key = os.getenv("SECRET_KEY", self.security.secret_key)
        self.security.encryption_key = os.getenv(
            "ENCRYPTION_KEY", self.security.encryption_key
        )

        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)

    def _validate(self):
        """Validate configuration."""
        errors = []
        if self.ai.provider not in {"openai", "anthropic", "gemini"}:
            errors.append(f"Unsupported AI provider '{self.ai.provider}'")

        if not self.ai.demo_mode:
            provider_config = self.ai.get_provider_config(self.ai.provider)
            if not provider_config.api_key or not provider_config.model:
                logger.warning(
                    f"{self.ai.provider} provider is not fully configured; AI-backed tools will return blocked responses"
                )

        if not any(p.enabled for p in self.platforms.values()):
            logger.warning("No marketing platforms configured")

        if not self.security.secret_key:
            self.security.secret_key = os.urandom(32).hex()
            logger.warning(
                "Generated process-local SECRET_KEY; set SECRET_KEY explicitly for stable token behavior"
            )

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

    def encrypt_value(self, value: str) -> str:
        """Encrypt a sensitive value."""
        if not self._cipher_suite:
            return value
        return self._cipher_suite.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a sensitive value."""
        if not self._cipher_suite:
            return encrypted_value
        return self._cipher_suite.decrypt(encrypted_value.encode()).decode()

    def get_platform_config(self, platform: str) -> Optional[PlatformConfig]:
        """Get configuration for a specific platform."""
        return self.platforms.get(platform.lower())

    def has_platform_credentials(self, platform: Any) -> bool:
        """Check whether a platform has enough credentials to attempt connection."""
        platform_name = platform.value if hasattr(platform, "value") else str(platform)
        config = self.get_platform_config(platform_name.lower())
        if not config:
            return False

        if isinstance(config, GoogleAdsConfig):
            return bool(
                config.developer_token
                and config.client_id
                and config.client_secret
                and config.refresh_token
                and config.customer_id
            )
        if isinstance(config, FacebookAdsConfig):
            return bool(config.app_id and config.app_secret and config.access_token)
        if isinstance(config, GoogleAnalyticsConfig):
            return bool(
                config.property_id
                and (
                    (config.client_id and config.client_secret and config.refresh_token)
                    or config.service_account_path
                )
            )
        return False

    def get_ai_provider_config(
        self, provider_name: Optional[str] = None
    ) -> ProviderConfig:
        """Return the configured AI provider configuration."""
        return self.ai.get_provider_config(provider_name)

    def save(self, config_path: str):
        """Save configuration to file without sensitive values."""
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
            "ai": {
                "provider": self.ai.provider,
                "demo_mode": self.ai.demo_mode,
                "openai": {
                    "model": self.ai.openai.model,
                    "max_tokens": self.ai.openai.max_tokens,
                    "temperature": self.ai.openai.temperature,
                },
                "anthropic": {
                    "model": self.ai.anthropic.model,
                    "max_tokens": self.ai.anthropic.max_tokens,
                    "temperature": self.ai.anthropic.temperature,
                },
                "gemini": {
                    "model": self.ai.gemini.model,
                    "max_tokens": self.ai.gemini.max_tokens,
                    "temperature": self.ai.gemini.temperature,
                },
            },
            "database": {
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow,
                "pool_timeout": self.database.pool_timeout,
                "echo": self.database.echo,
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

        with open(config_path, "w", encoding="utf-8") as handle:
            yaml.dump(data, handle, default_flow_style=False)
        logger.info(f"Configuration saved to {config_path}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a debug-safe dictionary."""
        return {
            "platforms_enabled": [
                name for name, config in self.platforms.items() if config.enabled
            ],
            "ai_provider": self.ai.provider,
            "demo_mode": self.ai.demo_mode,
            "openai_model": self.ai.openai.model,
            "anthropic_model": self.ai.anthropic.model,
            "gemini_model": self.ai.gemini.model,
            "database_url": (
                self.database.url.split("@")[0]
                if "@" in self.database.url
                else self.database.url
            ),
            "cache_enabled": self.performance.cache_enabled,
            "log_level": self.logging.level,
        }


_config: Optional[Config] = None


def get_config() -> Config:
    """Return the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def set_config(config: Config):
    """Override the global configuration instance."""
    global _config
    _config = config
