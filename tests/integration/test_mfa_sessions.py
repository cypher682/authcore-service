import pyotp


async def _register_and_authorize(client, email: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_mfa_setup_verify_and_disable(
    client,
    unique_email,
    strong_password,
) -> None:
    headers = await _register_and_authorize(client, unique_email, strong_password)

    setup_response = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_response.status_code == 200
    setup = setup_response.json()
    assert setup["is_enabled"] is False
    assert setup["provisioning_uri"].startswith("otpauth://")

    code = pyotp.TOTP(setup["secret"]).now()
    verify_response = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": code},
        headers=headers,
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["is_enabled"] is True

    disable_code = pyotp.TOTP(setup["secret"]).now()
    disable_response = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"code": disable_code},
        headers=headers,
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["is_enabled"] is False


async def test_enabled_mfa_requires_challenge_before_tokens(
    client,
    unique_email,
    strong_password,
) -> None:
    headers = await _register_and_authorize(client, unique_email, strong_password)

    setup_response = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_response.status_code == 200
    setup = setup_response.json()

    code = pyotp.TOTP(setup["secret"]).now()
    verify_response = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": code},
        headers=headers,
    )
    assert verify_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": strong_password},
    )
    assert login_response.status_code == 200
    challenge = login_response.json()
    assert challenge["mfa_required"] is True
    assert challenge["token_type"] == "mfa_challenge"
    assert "access_token" not in challenge
    assert "refresh_token" not in challenge

    bad_challenge_response = await client.post(
        "/api/v1/auth/mfa/challenge/verify",
        json={"challenge_token": challenge["challenge_token"], "code": "000000"},
    )
    assert bad_challenge_response.status_code == 400

    challenge_code = pyotp.TOTP(setup["secret"]).now()
    challenge_response = await client.post(
        "/api/v1/auth/mfa/challenge/verify",
        json={
            "challenge_token": challenge["challenge_token"],
            "code": challenge_code,
        },
    )
    assert challenge_response.status_code == 200
    tokens = challenge_response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["user"]["email"] == unique_email


async def test_user_can_list_and_delete_sessions(
    client,
    unique_email,
    strong_password,
) -> None:
    headers = await _register_and_authorize(client, unique_email, strong_password)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": strong_password},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    sessions_response = await client.get("/api/v1/users/me/sessions", headers=headers)
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert len(sessions) >= 2

    delete_response = await client.delete(
        f"/api/v1/users/me/sessions/{sessions[0]['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    remaining_response = await client.get("/api/v1/users/me/sessions", headers=headers)
    assert remaining_response.status_code == 200
    assert len(remaining_response.json()) == len(sessions) - 1
