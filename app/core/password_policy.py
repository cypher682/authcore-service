import hashlib
import re

import httpx

from app.core.config import settings

MIN_PASSWORD_LENGTH = 12
HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/{prefix}"
COMMON_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "qwerty123",
    "admin123",
    "letmein",
    "welcome",
    "iloveyou",
}


class PasswordPolicyError(ValueError):
    pass


def validate_password_strength(password: str, *, email: str | None = None) -> None:
    errors: list[str] = []

    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )

    if not re.search(r"[a-z]", password):
        errors.append("Password must include a lowercase letter")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must include an uppercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must include a number")

    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must include a symbol")

    normalized_password = password.lower()
    if normalized_password in COMMON_PASSWORDS:
        errors.append("Password is too common")

    if email:
        email_local_part = email.split("@", maxsplit=1)[0].lower()
        if email_local_part and email_local_part in normalized_password:
            errors.append("Password must not contain the email username")

    if errors:
        raise PasswordPolicyError("; ".join(errors))


async def validate_password_not_pwned(password: str) -> None:
    if not settings.password_breach_check_enabled:
        return

    sha1_password = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1_password[:5]
    suffix = sha1_password[5:]

    try:
        async with httpx.AsyncClient(timeout=settings.hibp_timeout_seconds) as client:
            response = await client.get(
                HIBP_RANGE_URL.format(prefix=prefix),
                headers={
                    "Add-Padding": "true",
                    "User-Agent": settings.app_title,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        if settings.password_breach_check_fail_closed:
            raise PasswordPolicyError(
                "Password breach check is temporarily unavailable"
            ) from exc
        return

    for line in response.text.splitlines():
        candidate_suffix, _, count = line.partition(":")
        if candidate_suffix == suffix:
            raise PasswordPolicyError(
                f"Password has appeared in known breaches {count} times"
            )
