import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pyotp
import bcrypt

from app.core.config import settings

BCRYPT_MAX_PASSWORD_BYTES = 72


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        return False

    hashed_password_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)


def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password must not exceed 72 bytes")

    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


# --- JWT Tokens ---
def create_access_token(subject: str | Any, scopes: list[str] | None = None) -> str:
    if scopes is None:
        scopes = []

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "scopes": scopes,
        "type": "access",
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.app_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | Any, family_id: str, scopes: list[str] | None = None
) -> str:
    if scopes is None:
        scopes = []

    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )

    # family_id allows us to track token chains and detect reuse
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "scopes": scopes,
        "type": "refresh",
        "family_id": family_id,
        "jti": str(uuid.uuid4()),  # Unique token ID
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.app_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """Decodes token and verifies expiration and signature."""
    try:
        payload = jwt.decode(
            token, settings.app_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


# --- MFA (TOTP) ---
def generate_totp_secret() -> str:
    return pyotp.random_base32()


def generate_totp_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=settings.app_title
    )


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
