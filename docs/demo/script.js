const state = {
  accessToken: "",
  refreshToken: "",
  oldRefreshToken: "",
  userId: "",
  adminAccessToken: "",
  adminId: "",
  roleId: "",
  permissionId: "",
  sessionId: "",
  mfaSecret: "",
};

const elements = {
  baseUrl: document.getElementById("baseUrl"),
  userEmail: document.getElementById("userEmail"),
  adminEmail: document.getElementById("adminEmail"),
  password: document.getElementById("password"),
  responses: document.getElementById("responses"),
  apiStatusDot: document.getElementById("apiStatusDot"),
  apiStatusText: document.getElementById("apiStatusText"),
  apiStatusDetail: document.getElementById("apiStatusDetail"),
  promoteCommand: document.getElementById("promoteCommand"),
};

function timestamp() {
  return new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
}

function seedValues() {
  const suffix = timestamp();
  elements.userEmail.value = `demo-user-${suffix}@example.com`;
  elements.adminEmail.value = `demo-admin-${suffix}@example.com`;
}

function baseUrl() {
  return elements.baseUrl.value.replace(/\/$/, "");
}

function password() {
  return elements.password.value;
}

function userEmail() {
  return elements.userEmail.value;
}

function adminEmail() {
  return elements.adminEmail.value;
}

function maskValue(value) {
  if (typeof value !== "string") {
    return value;
  }

  if (value.length <= 16) {
    return value;
  }

  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

function maskSensitive(data) {
  if (Array.isArray(data)) {
    return data.map(maskSensitive);
  }

  if (data && typeof data === "object") {
    return Object.fromEntries(
      Object.entries(data).map(([key, value]) => {
        const normalizedKey = key.toLowerCase();
        const isSensitive =
          normalizedKey.includes("token") ||
          normalizedKey.includes("secret") ||
          normalizedKey.includes("provisioning_uri");

        return [key, isSensitive ? maskValue(String(value)) : maskSensitive(value)];
      }),
    );
  }

  return data;
}

function addResponse(title, method, path, status, data) {
  const isError = status >= 400;
  const card = document.createElement("article");
  card.className = "response-card";
  card.innerHTML = `
    <div class="response-meta">
      <strong>${title}</strong>
      <span>${method} ${path}</span>
      <span class="badge ${isError ? "error" : ""}">HTTP ${status}</span>
    </div>
    <pre>${JSON.stringify(maskSensitive(data), null, 2)}</pre>
  `;
  elements.responses.prepend(card);
}

function setApiStatus(ok, detail) {
  elements.apiStatusDot.className = `dot ${ok ? "ok" : "bad"}`;
  elements.apiStatusText.textContent = ok ? "API reachable" : "API issue";
  elements.apiStatusDetail.textContent = detail;
}

async function apiRequest(title, method, path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
  };

  const response = await fetch(`${baseUrl()}${path}`, {
    method,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const text = await response.text();
  let data = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
  } else {
    data = { message: "No response body" };
  }

  addResponse(title, method, path, response.status, data);
  return { response, data };
}

async function healthCheck() {
  const result = await apiRequest("Health Check", "GET", "/health");
  setApiStatus(result.response.ok, result.response.ok ? "Health endpoint returned OK" : "Health request failed");
}

async function registerUser() {
  const result = await apiRequest("Register User", "POST", "/api/v1/auth/register", {
    body: { email: userEmail(), password: password() },
  });

  if (result.response.ok) {
    state.accessToken = result.data.access_token;
    state.refreshToken = result.data.refresh_token;
    state.oldRefreshToken = result.data.refresh_token;
    state.userId = result.data.user.id;
  }
}

async function loginUser() {
  const result = await apiRequest("Login User", "POST", "/api/v1/auth/login", {
    body: { email: userEmail(), password: password() },
  });

  if (result.response.ok) {
    state.accessToken = result.data.access_token;
    state.refreshToken = result.data.refresh_token;
  }
}

async function refreshToken() {
  state.oldRefreshToken = state.refreshToken;
  const result = await apiRequest("Refresh Token", "POST", "/api/v1/auth/refresh", {
    body: { refresh_token: state.refreshToken },
  });

  if (result.response.ok) {
    state.accessToken = result.data.access_token;
    state.refreshToken = result.data.refresh_token;
  }
}

async function reuseOldRefresh() {
  await apiRequest("Reuse Old Refresh Token", "POST", "/api/v1/auth/refresh", {
    body: { refresh_token: state.oldRefreshToken },
  });
}

async function setupMfa() {
  const result = await apiRequest("MFA Setup", "POST", "/api/v1/auth/mfa/setup", {
    token: state.accessToken,
  });

  if (result.response.ok) {
    state.mfaSecret = result.data.secret;
  }
}

function decodeBase32(secret) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const cleaned = secret.replace(/=+$/, "").replace(/\s+/g, "").toUpperCase();
  const bytes = [];
  let bits = 0;
  let value = 0;

  for (const character of cleaned) {
    const index = alphabet.indexOf(character);
    if (index === -1) {
      throw new Error("Invalid base32 character");
    }

    value = (value << 5) | index;
    bits += 5;

    if (bits >= 8) {
      bytes.push((value >>> (bits - 8)) & 255);
      bits -= 8;
    }
  }

  return new Uint8Array(bytes);
}

async function generateTotp(secret) {
  const keyBytes = decodeBase32(secret);
  const timeStep = Math.floor(Date.now() / 1000 / 30);
  const counter = new ArrayBuffer(8);
  const counterView = new DataView(counter);
  counterView.setUint32(4, timeStep);

  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "HMAC", hash: "SHA-1" },
    false,
    ["sign"],
  );
  const signature = new Uint8Array(await crypto.subtle.sign("HMAC", cryptoKey, counter));
  const offset = signature[signature.length - 1] & 15;
  const binary =
    ((signature[offset] & 127) << 24) |
    ((signature[offset + 1] & 255) << 16) |
    ((signature[offset + 2] & 255) << 8) |
    (signature[offset + 3] & 255);

  return String(binary % 1000000).padStart(6, "0");
}

async function verifyMfa() {
  const code = await generateTotp(state.mfaSecret);
  await apiRequest("MFA Verify", "POST", "/api/v1/auth/mfa/verify", {
    token: state.accessToken,
    body: { code },
  });
}

async function disableMfa() {
  const code = await generateTotp(state.mfaSecret);
  await apiRequest("MFA Disable", "POST", "/api/v1/auth/mfa/disable", {
    token: state.accessToken,
    body: { code },
  });
}

async function listSessions() {
  const result = await apiRequest("List Sessions", "GET", "/api/v1/users/me/sessions", {
    token: state.accessToken,
  });

  if (result.response.ok && result.data.length > 0) {
    state.sessionId = result.data[0].id;
  }
}

async function revokeSession() {
  await apiRequest("Revoke First Session", "DELETE", `/api/v1/users/me/sessions/${state.sessionId}`, {
    token: state.accessToken,
  });
}

async function registerAdmin() {
  const result = await apiRequest("Register Admin", "POST", "/api/v1/auth/register", {
    body: { email: adminEmail(), password: password() },
  });

  if (result.response.ok) {
    state.adminId = result.data.user.id;
  }
}

function showPromoteCommand() {
  elements.promoteCommand.textContent = `docker compose exec postgres psql -U authcore -d authcore_db -c "UPDATE users SET is_superuser = true WHERE email = '${adminEmail()}';"`;
}

async function loginAdmin() {
  const result = await apiRequest("Login Admin", "POST", "/api/v1/auth/login", {
    body: { email: adminEmail(), password: password() },
  });

  if (result.response.ok) {
    state.adminAccessToken = result.data.access_token;
  }
}

async function ensurePermission() {
  const permissions = await apiRequest("List Permissions", "GET", "/api/v1/admin/permissions", {
    token: state.adminAccessToken,
  });

  if (permissions.response.ok) {
    const existingPermission = permissions.data.find((permission) => permission.name === "admin:manage");
    if (existingPermission) {
      state.permissionId = existingPermission.id;
      addResponse("Use Existing admin:manage Permission", "LOCAL", "state.permissionId", 200, existingPermission);
      return;
    }
  }

  const created = await apiRequest("Create admin:manage Permission", "POST", "/api/v1/admin/permissions", {
    token: state.adminAccessToken,
    body: {
      name: "admin:manage",
      resource: "admin",
      action: "manage",
      description: "Allows protected admin manage route access",
    },
  });

  if (created.response.ok) {
    state.permissionId = created.data.id;
  }
}

async function createRole() {
  const result = await apiRequest("Create Demo Role", "POST", "/api/v1/admin/roles", {
    token: state.adminAccessToken,
    body: {
      name: `portfolio-admin-demo-${timestamp()}`,
      description: "Screenshot evidence role",
    },
  });

  if (result.response.ok) {
    state.roleId = result.data.id;
  }
}

async function attachPermission() {
  await apiRequest("Attach Permission To Role", "POST", `/api/v1/admin/roles/${state.roleId}/permissions`, {
    token: state.adminAccessToken,
    body: { permission_id: state.permissionId },
  });
}

async function assignRole() {
  await apiRequest("Assign Role To User", "POST", "/api/v1/admin/users/roles", {
    token: state.adminAccessToken,
    body: { user_id: state.userId, role_id: state.roleId },
  });
}

async function permissionCheck() {
  await apiRequest("RBAC Permission Check", "GET", "/api/v1/admin/rbac/permission-check", {
    token: state.accessToken,
  });
}

async function auditLogs() {
  await apiRequest("Audit Logs", "GET", "/api/v1/admin/audit-logs?limit=10", {
    token: state.adminAccessToken,
  });
}

async function badLogin() {
  await apiRequest("Bad Login", "POST", "/api/v1/auth/login", {
    body: { email: userEmail(), password: "WrongPassword123!" },
  });
}

async function runLockout() {
  for (let attempt = 1; attempt <= 6; attempt += 1) {
    await apiRequest(`Bad Login Attempt ${attempt}`, "POST", "/api/v1/auth/login", {
      body: { email: userEmail(), password: "WrongPassword123!" },
    });
  }
}

async function runRateLimit() {
  for (let attempt = 1; attempt <= 12; attempt += 1) {
    await apiRequest(`Bad Refresh Attempt ${attempt}`, "POST", "/api/v1/auth/refresh", {
      body: { refresh_token: `bad-token-${attempt}` },
    });
  }
}

function bindActions() {
  const bindings = {
    seedValues,
    healthCheck,
    registerUser,
    loginUser,
    refreshToken,
    reuseOldRefresh,
    setupMfa,
    verifyMfa,
    disableMfa,
    listSessions,
    revokeSession,
    registerAdmin,
    showPromoteCommand,
    loginAdmin,
    ensurePermission,
    createRole,
    attachPermission,
    assignRole,
    permissionCheck,
    auditLogs,
    badLogin,
    runLockout,
    runRateLimit,
  };

  for (const [id, handler] of Object.entries(bindings)) {
    document.getElementById(id).addEventListener("click", async () => {
      try {
        await handler();
      } catch (error) {
        addResponse("Browser/Network Error", "LOCAL", id, 500, {
          message: error.message,
        });
      }
    });
  }

  document.getElementById("clearResponses").addEventListener("click", () => {
    elements.responses.innerHTML = "";
  });
}

seedValues();
bindActions();
