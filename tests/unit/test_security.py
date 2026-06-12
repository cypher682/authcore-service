from app.core.security import (
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
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
