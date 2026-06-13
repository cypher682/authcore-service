from app.core.security import (
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.password_policy import (
    HIBP_RANGE_URL,
    PasswordPolicyError,
    validate_password_not_pwned,
    validate_password_strength,
)


def test_password_hash_verification() -> None:
    password = "StrongerPass123!"
    hashed_password = get_password_hash(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("WrongPass123!", hashed_password)


def test_refresh_token_contains_family_claim() -> None:
    token = create_refresh_token(subject="user-id", family_id="family-id")
    payload = decode_token(token)

    assert payload["sub"] == "user-id"
    assert payload["type"] == "refresh"
    assert payload["family_id"] == "family-id"
    assert payload["jti"]


def test_password_policy_accepts_strong_password() -> None:
    validate_password_strength(
        "StrongerPass123!",
        email="person@example.com",
    )


def test_password_policy_rejects_weak_password() -> None:
    try:
        validate_password_strength("password", email="person@example.com")
    except PasswordPolicyError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected weak password to fail policy")

    assert "at least 12 characters" in message
    assert "uppercase" in message
    assert "symbol" in message


def test_password_policy_rejects_email_username() -> None:
    try:
        validate_password_strength(
            "PersonStrong123!",
            email="person@example.com",
        )
    except PasswordPolicyError as exc:
        assert "email username" in str(exc)
    else:
        raise AssertionError("Expected password containing email username to fail")


async def test_hibp_check_rejects_breached_password(monkeypatch) -> None:
    import hashlib

    import httpx

    password = "StrongerPass123!"
    sha1_password = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1_password[:5]
    suffix = sha1_password[5:]

    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == HIBP_RANGE_URL.format(prefix=prefix)
        assert request.headers["Add-Padding"] == "true"
        return httpx.Response(
            200, text=f"{suffix}:42\n00000000000000000000000000000000000:1"
        )

    original_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.core.password_policy.settings.password_breach_check_enabled", True
    )
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **_: original_async_client(transport=httpx.MockTransport(handler)),
    )

    try:
        await validate_password_not_pwned(password)
    except PasswordPolicyError as exc:
        assert "known breaches 42 times" in str(exc)
    else:
        raise AssertionError("Expected breached password to fail")
