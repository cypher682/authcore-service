import uuid

from tests.conftest import make_superuser


async def test_admin_rbac_and_audit_query(
    client,
    unique_email,
    strong_password,
) -> None:
    admin_response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": strong_password},
    )
    assert admin_response.status_code == 201
    admin_user_id = admin_response.json()["user"]["id"]
    await make_superuser(unique_email)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": strong_password},
    )
    assert login_response.status_code == 200
    admin_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    permission_name = f"admin:test:{uuid.uuid4().hex}"
    permission_response = await client.post(
        "/api/v1/admin/permissions",
        json={
            "name": permission_name,
            "resource": "admin",
            "action": "test",
            "description": "Test permission",
        },
        headers=admin_headers,
    )
    assert permission_response.status_code == 201

    role_response = await client.post(
        "/api/v1/admin/roles",
        json={
            "name": f"test-role-{uuid.uuid4().hex}",
            "description": "Test role",
        },
        headers=admin_headers,
    )
    assert role_response.status_code == 201

    role_permission_response = await client.post(
        f"/api/v1/admin/roles/{role_response.json()['id']}/permissions",
        json={"permission_id": permission_response.json()["id"]},
        headers=admin_headers,
    )
    assert role_permission_response.status_code == 204

    users_response = await client.get(
        "/api/v1/admin/users?limit=5", headers=admin_headers
    )
    assert users_response.status_code == 200
    assert any(user["id"] == admin_user_id for user in users_response.json())

    audit_response = await client.get(
        "/api/v1/admin/audit-logs",
        params={"user_id": admin_user_id, "event_type": "rbac.role.created"},
        headers=admin_headers,
    )
    assert audit_response.status_code == 200
    assert any(
        log["event_type"] == "rbac.role.created" for log in audit_response.json()
    )
