"""
Security module for Marketing Automation MCP
Handles API key encryption, secure storage, and security auditing
"""

import os
import stat
import secrets
import hashlib
import base64
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import UTC, datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import keyring
import jwt
from dataclasses import dataclass
import json

from src.logger import get_logger, log_security_event

logger = get_logger(__name__)


def _require_secret_key() -> str:
    """Return the configured secret key or fail fast."""
    secret = os.getenv("SECRET_KEY")
    if not secret or secret == "replace-me":
        raise RuntimeError(
            "SECRET_KEY must be set before generating or validating session tokens."
        )
    return secret


@dataclass
class SecurityAuditResult:
    """Result of a security audit check"""

    key: str
    secure: bool
    status: str
    recommendations: List[str]


class SecureKeyManager:
    """Manage API keys and secrets securely"""

    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or os.getenv("MASTER_KEY")
        self._cipher_suite = None
        self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption with master key"""
        if not self.master_key:
            # Generate from machine ID for consistency
            machine_id = self._get_machine_id()
            self.master_key = self._derive_key(machine_id)

        # Create cipher suite
        if isinstance(self.master_key, str):
            self.master_key = self.master_key.encode()

        self._cipher_suite = Fernet(self.master_key)
        logger.info("Encryption initialized")

    def _get_machine_id(self) -> str:
        """Get unique machine identifier"""
        # Combine multiple sources for uniqueness
        components = []

        # MAC address
        try:
            import uuid

            mac = str(uuid.getnode())
            components.append(mac)
        except:
            pass

        # Hostname
        try:
            import socket

            hostname = socket.gethostname()
            components.append(hostname)
        except:
            pass

        # User
        components.append(os.getenv("USER", "default"))

        return "|".join(components)

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        salt = b"marketing_automation_mcp_2024"  # Static salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_key(self, api_key: str, key_name: str) -> str:
        """Encrypt an API key"""
        if not api_key:
            return ""

        try:
            encrypted = self._cipher_suite.encrypt(api_key.encode())

            log_security_event(
                logger,
                event_type="key_encrypted",
                severity="info",
                details={"key_name": key_name},
            )

            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt key {key_name}: {e}")
            raise

    def decrypt_key(self, encrypted_key: str, key_name: str) -> str:
        """Decrypt an API key"""
        if not encrypted_key:
            return ""

        try:
            decoded = base64.urlsafe_b64decode(encrypted_key.encode())
            decrypted = self._cipher_suite.decrypt(decoded)

            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt key {key_name}: {e}")
            raise

    def store_key_secure(self, service: str, key_name: str, api_key: str):
        """Store API key in system keyring"""
        try:
            # Encrypt before storing
            encrypted = self.encrypt_key(api_key, key_name)

            # Store in system keyring
            keyring.set_password(f"marketing_automation_{service}", key_name, encrypted)

            log_security_event(
                logger,
                event_type="key_stored",
                severity="info",
                details={"service": service, "key_name": key_name},
            )

        except Exception as e:
            logger.error(f"Failed to store key in keyring: {e}")
            # Fallback to encrypted file storage
            self._store_key_file(service, key_name, encrypted)

    def retrieve_key_secure(self, service: str, key_name: str) -> Optional[str]:
        """Retrieve API key from system keyring"""
        try:
            # Try keyring first
            encrypted = keyring.get_password(
                f"marketing_automation_{service}", key_name
            )

            if encrypted:
                return self.decrypt_key(encrypted, key_name)

            # Fallback to file storage
            return self._retrieve_key_file(service, key_name)

        except Exception as e:
            logger.error(f"Failed to retrieve key: {e}")
            return None

    def _store_key_file(self, service: str, key_name: str, encrypted_key: str):
        """Store encrypted key in file (fallback)"""
        keys_dir = Path.home() / ".marketing_automation" / "keys"
        keys_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions on directory
        os.chmod(keys_dir, stat.S_IRWXU)  # 700 - owner only

        key_file = keys_dir / f"{service}_{key_name}.key"
        key_file.write_text(encrypted_key)

        # Set restrictive permissions on file
        os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)  # 600 - owner read/write only

    def _retrieve_key_file(self, service: str, key_name: str) -> Optional[str]:
        """Retrieve encrypted key from file (fallback)"""
        key_file = (
            Path.home() / ".marketing_automation" / "keys" / f"{service}_{key_name}.key"
        )

        if key_file.exists():
            encrypted = key_file.read_text()
            return self.decrypt_key(encrypted, key_name)

        return None

    def rotate_master_key(self, new_master_key: str) -> bool:
        """Rotate the master encryption key"""
        try:
            # Get all stored keys
            stored_keys = self._get_all_stored_keys()

            # Decrypt with old key
            decrypted_keys = {}
            for service, keys in stored_keys.items():
                decrypted_keys[service] = {}
                for key_name, encrypted_value in keys.items():
                    try:
                        decrypted = self.decrypt_key(encrypted_value, key_name)
                        decrypted_keys[service][key_name] = decrypted
                    except:
                        logger.error(
                            f"Failed to decrypt {service}.{key_name} during rotation"
                        )

            # Update master key
            self.master_key = new_master_key.encode()
            self._init_encryption()

            # Re-encrypt with new key
            for service, keys in decrypted_keys.items():
                for key_name, value in keys.items():
                    self.store_key_secure(service, key_name, value)

            log_security_event(
                logger,
                event_type="master_key_rotated",
                severity="high",
                details={
                    "keys_rotated": sum(len(keys) for keys in decrypted_keys.values())
                },
            )

            return True

        except Exception as e:
            logger.error(f"Failed to rotate master key: {e}")
            return False

    def _get_all_stored_keys(self) -> Dict[str, Dict[str, str]]:
        """Get all stored keys for rotation"""
        stored_keys = {}

        # Check keyring
        # This would need to iterate through known services/keys
        # For now, return empty dict

        # Check file storage
        keys_dir = Path.home() / ".marketing_automation" / "keys"
        if keys_dir.exists():
            for key_file in keys_dir.glob("*.key"):
                parts = key_file.stem.split("_", 1)
                if len(parts) == 2:
                    service, key_name = parts
                    if service not in stored_keys:
                        stored_keys[service] = {}
                    stored_keys[service][key_name] = key_file.read_text()

        return stored_keys


class SecurityManager:
    """Manage overall security for the application"""

    def __init__(self):
        self.key_manager = SecureKeyManager()
        self._session_keys: Dict[str, Tuple[str, datetime]] = {}

    def audit_api_keys(self) -> List[SecurityAuditResult]:
        """Audit all API keys for security issues"""
        results = []

        # Check environment variables
        env_keys = [
            ("OPENAI_API_KEY", "OpenAI API Key"),
            ("GOOGLE_ADS_DEVELOPER_TOKEN", "Google Ads Token"),
            ("FACEBOOK_ACCESS_TOKEN", "Facebook Access Token"),
            ("GOOGLE_ANALYTICS_CLIENT_SECRET", "GA Client Secret"),
        ]

        for env_var, key_name in env_keys:
            value = os.getenv(env_var)

            if not value:
                results.append(
                    SecurityAuditResult(
                        key=key_name,
                        secure=True,
                        status="Not configured",
                        recommendations=[],
                    )
                )
                continue

            issues = []
            secure = True

            # Check if exposed in plain text
            if value.startswith("sk-") or value.startswith("pk-"):
                issues.append("Key appears to be in plain text")
                secure = False

            # Check length
            if len(value) < 20:
                issues.append("Key appears too short")
                secure = False

            # Check if it's a placeholder
            if value in ["your-api-key", "xxx", "test", "demo"]:
                issues.append("Key appears to be a placeholder")
                secure = False

            results.append(
                SecurityAuditResult(
                    key=key_name,
                    secure=secure,
                    status="Encrypted" if secure else "Security issues found",
                    recommendations=issues,
                )
            )

        return results

    def check_file_permissions(self) -> List[Dict[str, Any]]:
        """Check file permissions for sensitive files"""
        results = []

        sensitive_files = [
            Path.home() / ".marketing_automation" / "keys",
            Path(".env"),
            Path("config.yaml"),
            Path("credentials"),
        ]

        for file_path in sensitive_files:
            if not file_path.exists():
                continue

            stats = os.stat(file_path)
            mode = stats.st_mode

            # Check if world-readable
            world_readable = bool(mode & stat.S_IROTH)
            world_writable = bool(mode & stat.S_IWOTH)

            secure = not (world_readable or world_writable)

            results.append(
                {
                    "file": str(file_path),
                    "permissions": oct(mode)[-3:],
                    "secure": secure,
                    "world_readable": world_readable,
                    "world_writable": world_writable,
                }
            )

            if not secure:
                log_security_event(
                    logger,
                    event_type="insecure_file_permissions",
                    severity="high",
                    details={"file": str(file_path), "permissions": oct(mode)},
                )

        return results

    def check_environment_security(self) -> bool:
        """Check if environment is secure"""
        issues = []

        # Check debug mode
        if os.getenv("DEBUG", "").lower() == "true":
            issues.append("Debug mode is enabled")

        # Check for development indicators
        if os.getenv("ENV", "").lower() in ["dev", "development"]:
            issues.append("Running in development mode")

        # Check for exposed ports
        if os.getenv("HOST", "127.0.0.1") == "0.0.0.0":
            issues.append("Server exposed on all interfaces")

        if issues:
            log_security_event(
                logger,
                event_type="environment_security_check",
                severity="medium",
                details={"issues": issues},
            )

        return len(issues) == 0

    def generate_session_token(self, user_id: str, expiry_hours: int = 24) -> str:
        """Generate a secure session token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.now(UTC) + timedelta(hours=expiry_hours),
            "iat": datetime.now(UTC),
            "jti": secrets.token_urlsafe(16),  # Unique token ID
        }

        secret = _require_secret_key()
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Store for validation
        self._session_keys[payload["jti"]] = (user_id, payload["exp"])

        log_security_event(
            logger,
            event_type="session_created",
            severity="info",
            details={"user_id": user_id, "expiry_hours": expiry_hours},
        )

        return token

    def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a session token"""
        try:
            secret = _require_secret_key()
            payload = jwt.decode(token, secret, algorithms=["HS256"])

            # Check if token is in active sessions
            jti = payload.get("jti")
            if jti not in self._session_keys:
                return None

            # Check expiry
            if datetime.now(UTC) > datetime.fromtimestamp(payload["exp"], UTC):
                del self._session_keys[jti]
                return None

            return payload

        except jwt.InvalidTokenError:
            return None

    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage"""
        salt = os.getenv("HASH_SALT", "default_salt").encode()
        return hashlib.pbkdf2_hmac("sha256", data.encode(), salt, 100000).hex()

    def rotate_encryption_keys(self):
        """Rotate all encryption keys"""
        # Generate new master key
        new_master_key = Fernet.generate_key().decode()

        # Rotate in key manager
        success = self.key_manager.rotate_master_key(new_master_key)

        if success:
            # Save new key securely
            logger.info("Encryption keys rotated successfully")

            # You would typically store this in a secure key management service
            # For now, log that it needs to be updated
            logger.warning("Update MASTER_KEY environment variable with new key")

        return success

    def sanitize_log_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data before logging"""
        sensitive_keys = [
            "api_key",
            "token",
            "password",
            "secret",
            "credential",
            "access_token",
            "refresh_token",
            "client_secret",
        ]

        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 0:
                    # Show first 4 and last 4 characters
                    if len(value) > 10:
                        sanitized[key] = f"{value[:4]}...{value[-4:]}"
                    else:
                        sanitized[key] = "***"
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value

        return sanitized


# Global security manager instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


# Convenience functions
def secure_api_key(service: str, key_name: str, api_key: str):
    """Securely store an API key"""
    manager = get_security_manager()
    manager.key_manager.store_key_secure(service, key_name, api_key)


def retrieve_api_key(service: str, key_name: str) -> Optional[str]:
    """Retrieve a securely stored API key"""
    manager = get_security_manager()
    return manager.key_manager.retrieve_key_secure(service, key_name)


def audit_security() -> Dict[str, Any]:
    """Perform a complete security audit"""
    manager = get_security_manager()

    api_audit = manager.audit_api_keys()
    file_audit = manager.check_file_permissions()
    env_secure = manager.check_environment_security()

    # Calculate security score
    total_checks = len(api_audit) + len(file_audit) + 1
    passed_checks = sum(1 for r in api_audit if r.secure)
    passed_checks += sum(1 for r in file_audit if r["secure"])
    passed_checks += 1 if env_secure else 0

    security_score = (passed_checks / total_checks) * 100

    return {
        "security_score": round(security_score, 1),
        "api_keys": api_audit,
        "file_permissions": file_audit,
        "environment_secure": env_secure,
        "recommendations": _get_security_recommendations(
            api_audit, file_audit, env_secure
        ),
    }


def _get_security_recommendations(
    api_audit: List[SecurityAuditResult],
    file_audit: List[Dict[str, Any]],
    env_secure: bool,
) -> List[str]:
    """Generate security recommendations"""
    recommendations = []

    # API key recommendations
    insecure_keys = [r for r in api_audit if not r.secure]
    if insecure_keys:
        recommendations.append(
            "Encrypt or secure the following API keys: "
            + ", ".join(k.key for k in insecure_keys)
        )

    # File permission recommendations
    insecure_files = [f for f in file_audit if not f["secure"]]
    if insecure_files:
        for file in insecure_files:
            recommendations.append(
                f"Restrict permissions on {file['file']} (chmod 600)"
            )

    # Environment recommendations
    if not env_secure:
        recommendations.append("Ensure production environment settings are used")

    # General recommendations
    recommendations.extend(
        [
            "Rotate API keys regularly (every 90 days)",
            "Use environment-specific credentials",
            "Enable audit logging for all API access",
            "Implement rate limiting on all endpoints",
        ]
    )

    return recommendations
