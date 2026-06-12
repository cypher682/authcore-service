from fastapi import HTTPException, status

from app.core.config import settings
from app.core.redis import redis_client


async def check_login_lockout(*, email: str, ip_address: str | None) -> None:
    lockout_keys = _lockout_keys(email=email, ip_address=ip_address)
    for key in lockout_keys:
        if await redis_client.exists(key):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Too many failed login attempts. Try again later.",
            )


async def record_failed_login(*, email: str, ip_address: str | None) -> None:
    counter_keys = _counter_keys(email=email, ip_address=ip_address)
    for counter_key in counter_keys:
        attempts = await redis_client.incr(counter_key)
        if attempts == 1:
            await redis_client.expire(counter_key, settings.lockout_ttl_seconds)

        if attempts >= settings.max_failed_attempts:
            await redis_client.set(
                counter_key.replace("failed", "lockout"),
                "1",
                ex=settings.lockout_ttl_seconds,
            )


async def clear_failed_login(*, email: str, ip_address: str | None) -> None:
    keys = [
        *_counter_keys(email=email, ip_address=ip_address),
        *_lockout_keys(email=email, ip_address=ip_address),
    ]
    if keys:
        await redis_client.delete(*keys)


def _counter_keys(*, email: str, ip_address: str | None) -> list[str]:
    normalized_email = email.lower()
    keys = [f"authcore:login:failed:account:{normalized_email}"]
    if ip_address:
        keys.append(f"authcore:login:failed:ip:{ip_address}")
    return keys


def _lockout_keys(*, email: str, ip_address: str | None) -> list[str]:
    normalized_email = email.lower()
    keys = [f"authcore:login:lockout:account:{normalized_email}"]
    if ip_address:
        keys.append(f"authcore:login:lockout:ip:{ip_address}")
    return keys
