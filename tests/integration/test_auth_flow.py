async def test_register_login_refresh_and_reuse_detection(
    client,
    unique_email,
    strong_password,
) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": strong_password},
    )
    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["token_type"] == "bearer"
    assert registered["user"]["email"] == unique_email

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": strong_password},
    )
    assert login_response.status_code == 200
    login = login_response.json()

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"] != login["refresh_token"]

    reuse_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert reuse_response.status_code == 401


async def test_register_rejects_weak_password(client, unique_email) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "password"},
    )

    assert response.status_code == 422
    assert "at least 12 characters" in response.json()["detail"]


async def test_email_verification_flow(
    client,
    unique_email,
    strong_password,
    monkeypatch,
) -> None:
    sent_email: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.auth_service.send_verification_email.delay",
        lambda email, token: sent_email.update({"email": email, "token": token}),
    )

    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": strong_password},
    )

    assert register_response.status_code == 201
    assert register_response.json()["user"]["is_verified"] is False
    assert sent_email["email"] == unique_email

    verify_response = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": sent_email["token"]},
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["message"] == "Email verified successfully"


async def test_password_reset_flow_revokes_existing_refresh_token(
    client,
    unique_email,
    strong_password,
    monkeypatch,
) -> None:
    sent_reset: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.auth_service.send_verification_email.delay",
        lambda email, token: None,
    )
    monkeypatch.setattr(
        "app.services.auth_service.send_password_reset_email.delay",
        lambda email, token: sent_reset.update({"email": email, "token": token}),
    )
    new_password = "NewStrongerPass123!"

    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": strong_password},
    )
    assert register_response.status_code == 201
    original_refresh_token = register_response.json()["refresh_token"]

    forgot_response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": unique_email},
    )
    assert forgot_response.status_code == 200
    assert sent_reset["email"] == unique_email

    reset_response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": sent_reset["token"], "password": new_password},
    )
    assert reset_response.status_code == 200

    old_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": strong_password},
    )
    assert old_login_response.status_code == 401

    new_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": new_password},
    )
    assert new_login_response.status_code == 200

    old_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    assert old_refresh_response.status_code == 401
