async def test_failed_login_attempts_trigger_lockout(
    client,
    unique_email,
    strong_password,
) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": strong_password},
    )
    assert register_response.status_code == 201

    statuses = []
    for _ in range(6):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "WrongPass123!"},
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 423
