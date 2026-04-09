"""
services/security_service.py
─────────────────────────────
EncryptionManager: Fernet-based encryption for Groq API keys.
Password hashing with bcrypt.
"""

from __future__ import annotations
import bcrypt
from cryptography.fernet import Fernet, InvalidToken
import config


class EncryptionManager:
    """Handles symmetric encryption using Fernet (AES-128-CBC)."""

    def __init__(self) -> None:
        key = config.ENCRYPTION_KEY.encode() if config.ENCRYPTION_KEY else None
        if not key:
            raise RuntimeError(
                "ENCRYPTION_KEY is missing in .env. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return a base64-encoded token."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a Fernet token back to plaintext."""
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            raise ValueError("Decryption failed: invalid token or wrong key.")


# Module-level singleton
encryption_manager = EncryptionManager()


# ── Password Utilities ─────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())
