from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.config import Settings


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: UUID, role: str, settings: Settings) -> tuple[str, int]:
    lifetime = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + lifetime
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("Unexpected token type")
        return UUID(payload["sub"])
    except (InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise ValueError("Invalid or expired access token") from exc
