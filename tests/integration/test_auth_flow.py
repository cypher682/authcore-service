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
