# SGOD Platform — API Reference & AI-Agent Integration Guide

> Living reference for building an AI-chat assistant over SGOD (so a user can ask *“which assets do I own?”* in natural language instead of clicking a browser). **Scoped to the three services the assistant needs:** `auth` (login/session), `asset` (the data), and `chat` (optional). All endpoints, keys and samples below were **verified live** against `http://10.10.0.2:5007` on 2026-09-13.

---

## 1. How to access

### Hosts / ports

| Host | Role |
|---|---|
| `http://10.10.0.2:5007` | **API gateway** — routes *all* services + serves Swagger. Use this. |
| `http://10.10.0.2:5008` | Standalone `auth-service` deployment (auth only). |
| `http://10.10.0.2:8000` | Temporal Web UI (unrelated — not SGOD). |


Swagger UI per service: `http://10.10.0.2:5007/swagger/v1/<service>` (e.g. `.../asset-service`). There is **no `swagger.json`** — the OpenAPI spec is inlined in each page's `swagger-ui-init.js`.

### The services & their API keys

Every request needs **two credentials**: the service's static `x-api-key` **and** the user's `Authorization: Bearer <JWT>`. Keys follow the pattern `<SGOD_<SERVICE>_API_KEY>`:

| Service | Path prefix | `x-api-key` value | Ops | What it is |
|---|---|---|---|---|
| **auth-service** | `/sgod-auth/v1` | `<SGOD_AUTH_API_KEY>` | 179 | Identity & access: login, sessions, refresh, users, roles, permissions, departments, positions, org tree, MFA. |
| **asset-service** | `/sgod-asset/v1` | `<SGOD_ASSET_API_KEY>` | 100 | Asset lifecycle: assets, categories, locations, status/history, transfers, maintenance, staff requests, dashboards. |
| **chat-service** | `/sgod-chat/v1` | `<SGOD_CHAT_API_KEY>` | 62 | Realtime human-to-human messaging: conversations, participants, messages, reactions, drafts, blocks, moderation. |

> Scope: this guide covers the **three services your AI chat needs** — `auth` (so the chat can log the user in and hold the session), `asset` (the business data the user asks about), and `chat` (optional, if the assistant lives inside SGOD chat). Other SGOD services (upload, notification, payment, proposal) are intentionally out of scope here.

### Authentication flow

**1) Log in** (endpoint depends on the account tier):

```bash
curl -s -X POST "http://10.10.0.2:5007/sgod-auth/v1/enterprises/sessions" \
  -H "Content-Type: application/json" \
  -H "x-api-key: <SGOD_AUTH_API_KEY>" \
  -d '{"credential":"<SGOD_TEST_ACCOUNT_EMAIL>","password":"<SGOD_TEST_PASSWORD>"}'
# -> { "success": true, "data": { "accessToken":"eyJ...", "refreshToken":"..." } }
```

| Account tier | Login endpoint |
|---|---|
| Enterprise (tenant owner) | `POST /sgod-auth/v1/enterprises/sessions` |
| Enterprise User | `POST /sgod-auth/v1/enterprise-users/sessions` |
| Sub-Enterprise User | `POST /sgod-auth/v1/sub-enterprises/sessions` |
| SGOD platform user/admin | `POST /sgod-auth/v1/sgod-users/sessions` · `/sgod-admins/sessions` |

**2) Call any service** with the JWT + that service's key. One JWT works across **all** services (SSO):

```bash
TOKEN=<accessToken>
curl -s "http://10.10.0.2:5007/sgod-asset/v1/assets" \
  -H "x-api-key: <SGOD_ASSET_API_KEY>" \
  -H "Authorization: Bearer $TOKEN"
```

**3) Refresh** when the access token expires: `POST /sgod-auth/v1/sessions/refresh` (with the refresh token).

### Response envelope & error semantics *(important for the agent)*

Success and failure share one shape:

```json
{ "success": true,  "data": { ... }, "message": "...", "timestamp": "..." }
{ "success": false, "statusCode": 500, "error": "...", "message": "..." }
```

> ⚠️ The gateway sometimes returns **HTTP 200 even for server errors**, with the real code inside `body.statusCode`/`body.error`. **Always branch on `body.success`, not the HTTP status.**

### Identity scoping (the key idea for your use case)

Queries are **automatically scoped by the JWT** — e.g. `GET /sgod-asset/v1/assets` returns only the caller's tenant's assets; upload lists say *“identity is filtered by JWT.”* So the agent must authenticate **as the actual end-user** (their token), and 'which assets do I own' becomes a single scoped call — no explicit owner filter needed.


---

## 2. Services in detail

### auth-service  

`/sgod-auth/v1` · key `<SGOD_AUTH_API_KEY>` · 179 operations

**What it is.** The front door. Every other service trusts the JWT this service issues. It manages three account tiers (Enterprise owner, Enterprise User, Sub-Enterprise). It owns login, session/refresh, profile, RBAC (roles/permissions), and the org structure.

**Why the agent cares.** **This is how your AI chat authenticates the user and keeps the session alive.** The chat logs the user in here, holds their JWT, refreshes it, and answers 'who am I / my profile / my roles'. Every asset/chat call reuses this JWT.

**Feature groups:** `Test Crypto (PoC)`, `sgod-auth`, `sgod-auth-audit-logs`, `sgod-auth-departments`, `sgod-auth-email-verification`, `sgod-auth-enterprise`, `sgod-auth-enterprise-users`, `sgod-auth-iam-step-up`, `sgod-auth-organizations`, `sgod-auth-permissions`, `sgod-auth-positions`, `sgod-auth-roles`, `sgod-auth-sgod-admins`, `sgod-auth-sgod-enterprises`, `sgod-auth-sgod-users`, `sgod-auth-sub-enterprises`, `sgod-auth-users-organizational`

**Key endpoints (agent-relevant):**

| Method | Path | Meaning |
|---|---|---|
| `GET` | `/sgod-auth/v1/users/myself` | Get current user profile |
| `GET` | `/sgod-auth/v1/session/context` | Session context for SPA (SEC-PAM-01) |
| `POST` | `/sgod-auth/v1/enterprises/sessions` | Enterprise login |
| `POST` | `/sgod-auth/v1/sessions/refresh` | Refresh access token |
| `GET` | `/sgod-auth/v1/enterprises/profile` | Get enterprise profile |
| `GET` | `/sgod-auth/v1/enterprise-users` | Get enterprise users |
| `GET` | `/sgod-auth/v1/roles` | Get All Roles |
| `GET` | `/sgod-auth/v1/permissions` | Get all permissions |
| `GET` | `/sgod-auth/v1/departments/tree` | Get department tree |

**Sample I/O (live):**

*GET /sgod-auth/v1/users/myself — current user profile*

```json
{
  "success": true,
  "data": {
    "id": "6a85bad6a8d2133e058c93a9",
    "email": "<SGOD_TEST_ACCOUNT_EMAIL>",
    "userName": "<redacted>",
    "fullName": {
      "firstName": "<redacted>",
      "lastName": "<redacted>"
    },
    "userType": "enterprise",
    "roles": [
      "6a85bad6a8d2133e058c93aa"
    ],
    "phone": "<phone-redacted>",
    "status": "Active",
    "gender": "Other",
    "fallBackColor": "#34107a",
    "is2FAEnrolled": false,
    "enterpriseName": "<redacted>",
    "primaryRoleId": "6a85bad6a8d2133e058c93aa",
    "createdAt": "2026-08-19T14:16:54.595Z"
  },
  "message": "Profile retrieved successfully",
  "timestamp": "2026-09-13T
  ...(truncated)
```


### asset-service  

`/sgod-asset/v1` · key `<SGOD_ASSET_API_KEY>` · 100 operations

**What it is.** The core business domain. Assets belong to a tenant, sit in a category and a location, carry an auto QR code and sequential asset code, and move through status/transfer/maintenance workflows. Search is Elasticsearch-backed.

**Why the agent cares.** **This is the heart of your use case** ('which assets do I own', 'assets needing maintenance', 'where is asset X'). The JWT scopes every query to the caller's tenant automatically.

**Feature groups:** `sgod-asset-categories`, `sgod-asset-dashboard`, `sgod-asset-import-export`, `sgod-asset-locations`, `sgod-asset-maintenance`, `sgod-asset-offer`, `sgod-asset-report-template`, `sgod-asset-request-staff`, `sgod-asset-status`, `sgod-asset-transfers`, `sgod-assets`, `sgod-categories-offer`

**Key endpoints (agent-relevant):**

| Method | Path | Meaning |
|---|---|---|
| `GET` | `/sgod-asset/v1/assets` | List assets (FindAllAssets) |
| `GET` | `/sgod-asset/v1/assets/{id}` | Get asset by id (FindAssetById) |
| `GET` | `/sgod-asset/v1/assets/suggest` | Gợi ý / autocomplete tên tài sản (search-as-you-type via Elasticsearch) |
| `POST` | `/sgod-asset/v1/assets` | Create asset (asset.v1 CreateAsset) |
| `GET` | `/sgod-asset/v1/categories` | List categories flat (ListCategories) |
| `GET` | `/sgod-asset/v1/locations` | List locations flat (ListLocations) |
| `GET` | `/sgod-asset/v1/asset-transfers` | Danh sách phiếu chuyển giao tài sản — ListAssetTransfers |
| `GET` | `/sgod-asset/v1/maintenance/schedules` | List maintenance schedules (ListMaintenanceSchedules) |
| `GET` | `/sgod-asset/v1/dashboard/statistics-asset` | Asset status time series (v1 parity) |
| `GET` | `/sgod-asset/v1/request-staff` | Danh sách request staff — ListRequestStaff |

**Sample I/O (live):**

*GET /sgod-asset/v1/assets?limit=5 — my assets (JWT-scoped)*

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "aliasNames": [],
        "images": [],
        "files": [],
        "locations": [],
        "id": "6aa2c177da46d70ee2f491c1",
        "name": "QA Test Laptop",
        "assetCode": "000000001",
        "description": "",
        "enterpriseId": "6a85bad6a8d2133e058c93a9",
        "categoryId": "6aa2c134da46d70ee2f491bf",
        "status": "active",
        "totalQuantity": 0,
        "initialQuantity": 0,
        "unit": "piece",
        "assetType": "normal",
        "isImportant": false,
        "onBlockchain": false,
        "createdBy": "6a85bad6a8d2133e058c93a9",
        "
  ...(truncated)
```

*GET /sgod-asset/v1/assets/{id} — one asset (auto assetCode + qrCode)*

```json
{
  "success": true,
  "data": {
    "asset": {
      "aliasNames": [],
      "images": [],
      "files": [],
      "locations": [],
      "id": "6aa2c177da46d70ee2f491c1",
      "name": "QA Test Laptop",
      "assetCode": "000000001",
      "description": "",
      "enterpriseId": "6a85bad6a8d2133e058c93a9",
      "categoryId": "6aa2c134da46d70ee2f491bf",
      "status": "active",
      "totalQuantity": 0,
      "initialQuantity": 0,
      "unit": "piece",
      "assetType": "normal",
      "isImportant": false,
      "onBlockchain": false,
      "createdBy": "6a85bad6a8d2133e058c93a9",
      "createdAt": "1789051255761",
      "updatedAt"
  ...(truncated)
```


### chat-service  

`/sgod-chat/v1` · key `<SGOD_CHAT_API_KEY>` · 62 operations

**What it is.** A Slack/WhatsApp-style backend. REST manages conversations/participants and **reads** message history; **sending** is over Socket.IO. Multi-tenant, with roles, read-state, mute/pin/archive, E2EE and moderation.

**Why the agent cares.** Relevant if your AI chat is delivered *inside* SGOD chat (as a bot participant) or if the agent answers 'my unread messages'. Note the role limitation below.

**Feature groups:** `Chat - Conversations`, `Chat - Drafts`, `Chat - Messages`, `Chat - Participants`, `Chat - Poolings`, `Chat - Reactions`, `Chat - Recipients`, `Chat - Reports`, `Chat - Settings`, `Chat - Sync`, `Chat - User Blocks`

**Key endpoints (agent-relevant):**

| Method | Path | Meaning |
|---|---|---|
| `GET` | `/sgod-chat/v1/conversations` | Get conversations with pagination |
| `GET` | `/sgod-chat/v1/conversations/unread-counts` | Get unread counts |
| `POST` | `/sgod-chat/v1/conversations/private` | Get or create a private conversation |
| `POST` | `/sgod-chat/v1/conversations/group` | Create a new group conversation |
| `GET` | `/sgod-chat/v1/messages` | Get messages by conversation |
| `GET` | `/sgod-chat/v1/settings/current` | Get Current User Setting |

**Sample I/O (live):**

*GET /sgod-chat/v1/conversations — my conversations*

```json
{
  "success": true,
  "data": {
    "conversations": [
      {
        "id": "6aa2c5e2e8667af3ad1333ff",
        "tenantId": "6a85bad6a8d2133e058c93a9",
        "type": "group",
        "title": "QA Project Team",
        "logoId": "",
        "members": [
          {
            "tenantId": "6a85bad6a8d2133e058c93a9",
            "belongTo": "Enterprise",
            "userId": "6a85bad6a8d2133e058c93a9"
          },
          {
            "tenantId": "6a85bad6a8d2133e058c93a9",
            "belongTo": "EnterpriseUser",
            "userId": "6a85be56a8d2133e058c93b9"
          },
          {
            "tenantId": "6a85bad6a8d2133e058c93a
  ...(truncated)
```


---

## 3. AI-agent integration (your chat assistant)

### How the assistant handles auth (do this once, at chat start)

The assistant is responsible for authentication so the user never touches a browser:

1. **Collect credentials** (email + password) in the chat, or accept an existing token from your app.
2. **Log in** at the tier endpoint → store `accessToken` + `refreshToken` for the session:
   `POST /sgod-auth/v1/<tier>/sessions` where `<tier>` ∈ `enterprises` · `enterprise-users` · `sub-enterprises`.
   *Tip:* if the tier is unknown, `POST /sgod-auth/v1/emails/check-exists {email}` returns the `accountType` so you can pick the right endpoint.
3. **Load context** once: `GET /sgod-auth/v1/users/myself` (profile) and `GET /sgod-auth/v1/session/context` (roles/permissions) — so the assistant knows who it is acting as.
4. **Attach headers to every call**: `x-api-key: <service key>` + `Authorization: Bearer <accessToken>`. One token works for auth **and** asset **and** chat (SSO).
5. **Refresh silently** on `401`/expiry: `POST /sgod-auth/v1/sessions/refresh` with the refresh token; retry the original call.
6. **Log out / end session**: `DELETE /sgod-auth/v1/sessions`.

> The assistant should keep the raw `password` only long enough to log in, then rely on the tokens. Store the service `x-api-key`s in the tool/MCP backend, never in the model context.

### Natural-language intent → API call

| User says (in chat) | Agent calls | Notes |
|---|---|---|
| “Log me in” (chat start) | `POST /sgod-auth/v1/<tier>/sessions` | tier = enterprises / enterprise-users / sub-enterprises |
| “Who am I / my profile” | `GET /sgod-auth/v1/users/myself` | identity from JWT |
| “My roles / permissions” | `GET /sgod-auth/v1/session/context` | roles + permissions for the session |
| (session expiring) | `POST /sgod-auth/v1/sessions/refresh` | agent refreshes silently |
| **“Which assets do I own?”** | `GET /sgod-asset/v1/assets` | JWT-scoped to tenant; paginate with `?limit&cursor` |
| “Show asset &lt;name&gt;” | `GET /sgod-asset/v1/assets/suggest?q=<name>` → `GET /assets/{id}` | resolve name→id, then fetch |
| “Assets needing maintenance” | `GET /sgod-asset/v1/maintenance/schedules` | filter by status |
| “Where is asset X / its location” | `GET /sgod-asset/v1/assets/{id}` + `GET /locations/{id}` | |
| “My asset transfers” | `GET /sgod-asset/v1/asset-transfers` | |
| “How many assets by status” | `GET /sgod-asset/v1/dashboard/statistics-asset` | |
| “My conversations” | `GET /sgod-chat/v1/conversations` | Enterprise-owner only today (see issues) |
| “My unread messages” | `GET /sgod-chat/v1/conversations/unread-counts` | Enterprise-owner only today (see issues) |

### Worked scenario — “which assets do I own?”

```text
User (in AI chat):  "which assets am I owning?"
  │
  1. Agent already holds the user's JWT (from login at chat start).
  2. Agent -> GET /sgod-asset/v1/assets   [x-api-key: ...asset] [Bearer <user JWT>]
  3. Service auto-scopes to the user's tenant and returns the list.
  4. Agent formats a natural-language answer.
```

Real call & response:

```bash
curl -s "http://10.10.0.2:5007/sgod-asset/v1/assets?limit=5" \
  -H "x-api-key: <SGOD_ASSET_API_KEY>" -H "Authorization: Bearer $TOKEN"
```

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "aliasNames": [],
        "images": [],
        "files": [],
        "locations": [],
        "id": "6aa2c177da46d70ee2f491c1",
        "name": "QA Test Laptop",
        "assetCode": "000000001",
        "description": "",
        "enterpriseId": "6a85bad6a8d2133e058c93a9",
        "categoryId": "6aa2c134da46d70ee2f491bf",
        "status": "active",
        "totalQuantity": 0,
        "initialQuantity": 0,
        "unit": "piece",
        "assetType": "normal",
        "isImportant": false,
        "onBlockchain": false,
        "createdBy": "6a85bad6a8d2133e058c93a9",
        "
  ...(truncated)
```

→ Agent replies: *“You own **1** asset: **QA Test Laptop** (code `000000001`, status `active`, unit: piece).”*

### Recommended agent tool surface

- **Start read-only.** Expose the `GET` endpoints in the intent table as agent tools first; gate all writes (create asset, transfers, blocks) behind confirmation.
- **Centralise auth in the tool layer** (an MCP server or tool backend): it holds the 7 service keys, performs login/refresh, injects both headers. The agent never sees secrets — it just calls `list_my_assets()` etc.
- **Bind each session to one end-user's JWT** so scoping is automatic and correct per tenant.
- **Curate, don't dump.** ~482 endpoints is far too many raw tools; start with ~15–25 high-value ones.


---

## 4. Known issues & maturity (found during live testing)

| Sev | Service | Endpoint / area | Symptom |
|---|---|---|---|
| High | chat | all endpoints for non-owner | `500` for Enterprise-User & Sub-Enterprise tokens; only the **Enterprise owner** works (reproduced 8/8). Blocks chat for sub-accounts. |
| Med | chat | JWT validation | Intermittent `16 UNAUTHENTICATED: Auth JWKS gRPC client not ready` for everyone. |
| Info | chat | message send | No REST send; messages go over **Socket.IO** (`SendMessage` event). REST only reads. |
| Med | asset | `GET /dashboard/summary` | `this.assetRepo.countSummary is not a function` (500). |
| Med | asset | `GET /maintenance/schedules/count-by-tab` | gRPC `CountMaintenanceScheduleTabs not found`. |
| Med | asset | `GET /import-export/exports` | gRPC `ListAssetExports not found`. |
| Med | asset | `GET /asset-offers`, `GET /categories-offer` | `No handler found` (CQRS query unregistered). |
| Low | auth | account `<sub-enterprise-test-account>` | exists as SUBENTERPRISE but rejects the shared password (`Invalid credentials`). |
| Info | all | error masking | Errors return **HTTP 200** with `body.statusCode` = real code. Branch on `success`. |
| Info | asset/others | some create bodies | Swagger shows opaque `{"root":null}`; required fields must be learned from validation errors. |


---

## 5. Appendix — full endpoint inventory

Total: **341** operations across 3 services (auth, asset, chat).

<details><summary><b>auth-service</b> — 179 ops</summary>


**Test Crypto (PoC)**

| Method | Path | Summary |
|---|---|---|
| POST | `/sgod-auth/v1/test-crypto/decrypt-file-helper` | Test helper DecryptFileStream using binary uploads |
| POST | `/sgod-auth/v1/test-crypto/decrypt-string-helper` | Test helper DecryptString dùng chung với phân quyền |
| POST | `/sgod-auth/v1/test-crypto/encrypt-file-helper` | Test helper EncryptFileStream using binary streams |
| POST | `/sgod-auth/v1/test-crypto/encrypt-string-helper` | Test helper EncryptString dùng chung |

**health**

| Method | Path | Summary |
|---|---|---|
| GET | `/health` | Health check endpoint - Supports auth, chat, upload, notification, mailer, payment, proposal |
| GET | `/health/grpc` | Check gRPC connection health - Supports auth, chat, upload, notification, mailer, payment |
| GET | `/health/mailer` | Check notification-service mailer health |

**sgod-auth**

| Method | Path | Summary |
|---|---|---|
| POST | `/sgod-auth/v1/activate-account` | Activate account for emplyee account (when they first time login) |
| GET | `/sgod-auth/v1/dev/emails` | [DEV ONLY] Retrieve sent dev email logs and latest token |
| POST | `/sgod-auth/v1/devices/{deviceId}/trust` | Trust a device |
| POST | `/sgod-auth/v1/devices/{deviceId}/untrust` | Untrust a device |
| POST | `/sgod-auth/v1/enterprise-users/sessions` | Enterprise user login |
| POST | `/sgod-auth/v1/enterprises/sessions` | Enterprise login |
| POST | `/sgod-auth/v1/mfa/disable` | Disable 2FA |
| POST | `/sgod-auth/v1/mfa/enable` | Enable 2FA |
| POST | `/sgod-auth/v1/mfa/unenroll` | Remove 2FA enrollment |
| POST | `/sgod-auth/v1/mfa/verification` | Verify 2FA setup |
| POST | `/sgod-auth/v1/mfa/verify` | Verify 2FA during login |
| POST | `/sgod-auth/v1/passwords/change` | Change password |
| POST | `/sgod-auth/v1/passwords/forgot` | Forgot password |
| POST | `/sgod-auth/v1/passwords/reset` | Reset password |
| GET | `/sgod-auth/v1/session/context` | Session context for SPA (SEC-PAM-01) |
| DELETE | `/sgod-auth/v1/sessions` | Logout from all devices |
| POST | `/sgod-auth/v1/sessions/current` | Logout from current session |
| GET | `/sgod-auth/v1/sessions/devices` | List all devices |
| DELETE | `/sgod-auth/v1/sessions/devices/{deviceId}` | Logout from one device |
| POST | `/sgod-auth/v1/sessions/refresh` | Refresh access token |
| POST | `/sgod-auth/v1/sgod-admins/sessions` | SGOD admin login |
| POST | `/sgod-auth/v1/sgod-users/sessions` | SGOD user login |
| POST | `/sgod-auth/v1/sub-enterprises/sessions` | Sub-enterprise login |
| GET | `/sgod-auth/v1/users/myself` | Get current user profile |
| GET | `/sgod-auth/v1/users/myself/profile-with-assets` | Get current user profile with avatar/logo URLs from upload |
| PATCH | `/sgod-auth/v1/users/myself/profile-with-assets` | Update profile and/or upload avatar & logo (BFF) |
| POST | `/sgod-auth/v1/users/{userId}/actions/initiate-reset-password` | Initiate password reset for user |
| POST | `/sgod-auth/v1/users/{userId}/actions/resend-activation` | Resend SGOD account activation email |

**sgod-auth-audit-logs**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/sgod/audit-logs` | Get audit logs |

**sgod-auth-departments**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/departments` | Get all departments |
| POST | `/sgod-auth/v1/departments` | Create department |
| GET | `/sgod-auth/v1/departments/deleted` | Get deleted departments |
| GET | `/sgod-auth/v1/departments/statistics` | Get departments statistics |
| GET | `/sgod-auth/v1/departments/tree` | Get department tree |
| POST | `/sgod-auth/v1/departments/{departmentId}/move` | Move department |
| GET | `/sgod-auth/v1/departments/{departmentId}/statistics` | Get department statistics |
| GET | `/sgod-auth/v1/departments/{departmentId}/users` | Get users by department |
| DELETE | `/sgod-auth/v1/departments/{id}` | Delete department |
| GET | `/sgod-auth/v1/departments/{id}` | Get department by ID |
| PATCH | `/sgod-auth/v1/departments/{id}` | Update department |
| POST | `/sgod-auth/v1/departments/{id}/restore` | Restore department |

**sgod-auth-email-verification**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/emails/check` | Check email existence |
| POST | `/sgod-auth/v1/emails/check-exists` | Check if email exists (POST method) |
| POST | `/sgod-auth/v1/emails/payment-code` | Create payment verification code |
| POST | `/sgod-auth/v1/emails/payment-code/verify` | Verify payment code |
| POST | `/sgod-auth/v1/emails/send` | Send OTP verification email |
| GET | `/sgod-auth/v1/emails/token` | Get latest token (Dev mode only) |
| POST | `/sgod-auth/v1/emails/verifications/code` | Verify email OTP |
| POST | `/sgod-auth/v1/emails/verify` | Verify email OTP |

**sgod-auth-enterprise**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/enterprises/profile` | Get enterprise profile |
| POST | `/sgod-auth/v1/enterprises/register` | Register enterprise |
| POST | `/sgod-auth/v1/enterprises/verifications/resend-otp` | Resend verification OTP - it will return OTP code directly in dev mode |

**sgod-auth-enterprise-users**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/enterprise-users` | Get enterprise users |
| POST | `/sgod-auth/v1/enterprise-users` | Create enterprise user |
| GET | `/sgod-auth/v1/enterprise-users/deleted` | Get deleted enterprise users |
| PATCH | `/sgod-auth/v1/enterprise-users/me` | Update my profile (me alias) |
| PATCH | `/sgod-auth/v1/enterprise-users/my-profile` | Update my profile |
| PATCH | `/sgod-auth/v1/enterprise-users/profile` | Update my profile (alias) |
| GET | `/sgod-auth/v1/enterprise-users/statistics` | Get enterprise users statistics |
| DELETE | `/sgod-auth/v1/enterprise-users/{userId}` | Delete enterprise user |
| GET | `/sgod-auth/v1/enterprise-users/{userId}` | Get enterprise user profile |
| PATCH | `/sgod-auth/v1/enterprise-users/{userId}` | Update enterprise user |
| GET | `/sgod-auth/v1/enterprise-users/{userId}/available-bosses` | Get available bosses for enterprise user |
| POST | `/sgod-auth/v1/enterprise-users/{userId}/block` | Block enterprise user |
| PATCH | `/sgod-auth/v1/enterprise-users/{userId}/boss` | Set boss for enterprise user |
| PATCH | `/sgod-auth/v1/enterprise-users/{userId}/department-position` | Assign department/position to enterprise user |
| DELETE | `/sgod-auth/v1/enterprise-users/{userId}/position` | Remove enterprise user from position |
| POST | `/sgod-auth/v1/enterprise-users/{userId}/restore` | Restore enterprise user |
| POST | `/sgod-auth/v1/enterprise-users/{userId}/revoke-wallet-key` | Revoke user wallet key |
| PATCH | `/sgod-auth/v1/enterprise-users/{userId}/roles` | Assign roles to enterprise user |
| POST | `/sgod-auth/v1/enterprise-users/{userId}/unblock` | Unblock enterprise user |

**sgod-auth-iam-step-up**

| Method | Path | Summary |
|---|---|---|
| POST | `/sgod-auth/v1/iam/step-up` | Verify IAM step-up MFA (Redis session grant) |

**sgod-auth-organizations**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/organizations/audit` | Audit organizational structure reporting lines |

**sgod-auth-permissions**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/permissions` | Get all permissions |

**sgod-auth-positions**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/positions` | Get all positions |
| POST | `/sgod-auth/v1/positions` | Create position |
| GET | `/sgod-auth/v1/positions/available` | Get available positions |
| GET | `/sgod-auth/v1/positions/deleted` | Get deleted positions |
| POST | `/sgod-auth/v1/positions/preview-change` | Preview position hierarchy change (dry-run) |
| GET | `/sgod-auth/v1/positions/statistics` | Get positions statistics |
| GET | `/sgod-auth/v1/positions/tree` | Get position tree |
| DELETE | `/sgod-auth/v1/positions/{id}` | Delete position |
| GET | `/sgod-auth/v1/positions/{id}` | Get position by ID |
| PATCH | `/sgod-auth/v1/positions/{id}` | Update position |
| POST | `/sgod-auth/v1/positions/{id}/restore` | Restore position |
| GET | `/sgod-auth/v1/positions/{positionId}/users` | Get users by position |

**sgod-auth-roles**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/roles` | Get All Roles |
| POST | `/sgod-auth/v1/roles` | Create Role |
| GET | `/sgod-auth/v1/roles/creatable-layers` | Get creatable role layers |
| GET | `/sgod-auth/v1/roles/deleted` | Get deleted roles |
| GET | `/sgod-auth/v1/roles/statistics` | Get roles statistics |
| GET | `/sgod-auth/v1/roles/tenant/{tenantId}` | Get Roles by Tenant |
| GET | `/sgod-auth/v1/roles/tree` | Get Role Tree |
| GET | `/sgod-auth/v1/roles/tree/{rootRoleId}` | Get Role Tree from Root |
| DELETE | `/sgod-auth/v1/roles/{id}` | Delete Role |
| GET | `/sgod-auth/v1/roles/{id}` | Get Role by ID |
| PATCH | `/sgod-auth/v1/roles/{id}` | Update Role |
| GET | `/sgod-auth/v1/roles/{id}/available-parents` | Get Available Parent Roles |
| PATCH | `/sgod-auth/v1/roles/{id}/move` | Move Role Hierarchy |
| POST | `/sgod-auth/v1/roles/{id}/restore` | Restore Role |
| GET | `/sgod-auth/v1/roles/{id}/users` | Get Users by Role |

**sgod-auth-sgod-admins**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/sgod/admins` | Get all SGOD admins |
| POST | `/sgod-auth/v1/sgod/admins` | Create SGOD admin |
| GET | `/sgod-auth/v1/sgod/admins/deleted` | Get deleted SGOD admins |
| PATCH | `/sgod-auth/v1/sgod/admins/me` | Update my profile (me alias) |
| PATCH | `/sgod-auth/v1/sgod/admins/my-profile` | Update my profile |
| PATCH | `/sgod-auth/v1/sgod/admins/profile` | Update my profile (alias) |
| GET | `/sgod-auth/v1/sgod/admins/statistics` | Thống kê tổng quan SGOD Admin |
| DELETE | `/sgod-auth/v1/sgod/admins/{adminId}` | Delete SGOD admin |
| GET | `/sgod-auth/v1/sgod/admins/{adminId}` | Get SGOD admin profile |
| PATCH | `/sgod-auth/v1/sgod/admins/{adminId}` | Update SGOD admin |
| POST | `/sgod-auth/v1/sgod/admins/{adminId}/block` | Block SGOD admin |
| DELETE | `/sgod-auth/v1/sgod/admins/{adminId}/permanent` | Hard delete SGOD admin (Root Admin only) |
| POST | `/sgod-auth/v1/sgod/admins/{adminId}/restore` | Restore SGOD admin |
| POST | `/sgod-auth/v1/sgod/admins/{adminId}/unblock` | Unblock SGOD admin |
| GET | `/sgod-auth/v1/sgod/admins/{userId}/available-bosses` | Get available bosses for SGOD admin |
| PATCH | `/sgod-auth/v1/sgod/admins/{userId}/boss` | Set boss for SGOD admin |
| PATCH | `/sgod-auth/v1/sgod/admins/{userId}/department-position` | Assign department/position to SGOD admin |
| PATCH | `/sgod-auth/v1/sgod/admins/{userId}/roles` | Assign roles to SGOD admin |

**sgod-auth-sgod-enterprises**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/sgod/enterprises` | List SGOD enterprises |
| POST | `/sgod-auth/v1/sgod/enterprises/assign` | Assign enterprises to user |
| GET | `/sgod-auth/v1/sgod/enterprises/deleted` | Get deleted enterprises |
| POST | `/sgod-auth/v1/sgod/enterprises/set-assigned` | Set assigned enterprises for user |
| GET | `/sgod-auth/v1/sgod/enterprises/statistics/overview` | Thống kê tổng quan doanh nghiệp toàn sàn |
| POST | `/sgod-auth/v1/sgod/enterprises/unassign` | Unassign enterprise from user |
| GET | `/sgod-auth/v1/sgod/enterprises/{tenantId}` | Get enterprise details |
| POST | `/sgod-auth/v1/sgod/enterprises/{tenantId}/block` | Block enterprise |
| PATCH | `/sgod-auth/v1/sgod/enterprises/{tenantId}/features` | Update enterprise features |
| POST | `/sgod-auth/v1/sgod/enterprises/{tenantId}/restore` | Restore enterprise |
| GET | `/sgod-auth/v1/sgod/enterprises/{tenantId}/statistics` | Get enterprise statistics |
| PATCH | `/sgod-auth/v1/sgod/enterprises/{tenantId}/subscription` | Update enterprise subscription |
| POST | `/sgod-auth/v1/sgod/enterprises/{tenantId}/unblock` | Unblock enterprise |

**sgod-auth-sgod-users**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/sgod-users` | Get SGOD users |
| POST | `/sgod-auth/v1/sgod-users` | Create SGOD user |
| GET | `/sgod-auth/v1/sgod-users/deleted` | Get deleted SGOD users |
| PATCH | `/sgod-auth/v1/sgod-users/me` | Update my profile (me alias) |
| PATCH | `/sgod-auth/v1/sgod-users/my-profile` | Update my profile |
| PATCH | `/sgod-auth/v1/sgod-users/profile` | Update my profile (alias) |
| GET | `/sgod-auth/v1/sgod-users/statistics` | Thống kê tổng quan SGOD User |
| DELETE | `/sgod-auth/v1/sgod-users/{userId}` | Delete SGOD user |
| GET | `/sgod-auth/v1/sgod-users/{userId}` | Get SGOD user profile |
| PATCH | `/sgod-auth/v1/sgod-users/{userId}` | Update SGOD user |
| GET | `/sgod-auth/v1/sgod-users/{userId}/available-bosses` | Get available bosses for SGOD user |
| POST | `/sgod-auth/v1/sgod-users/{userId}/block` | Block SGOD user |
| PATCH | `/sgod-auth/v1/sgod-users/{userId}/boss` | Set boss for SGOD user |
| PATCH | `/sgod-auth/v1/sgod-users/{userId}/department-position` | Assign department/position to SGOD user |
| DELETE | `/sgod-auth/v1/sgod-users/{userId}/permanent` | Hard delete SGOD user (Root Admin only) |
| POST | `/sgod-auth/v1/sgod-users/{userId}/restore` | Restore SGOD user |
| PATCH | `/sgod-auth/v1/sgod-users/{userId}/roles` | Assign roles to SGOD user |
| POST | `/sgod-auth/v1/sgod-users/{userId}/unblock` | Unblock SGOD user |

**sgod-auth-sub-enterprises**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-auth/v1/sub-enterprises` | Get sub-enterprises |
| POST | `/sgod-auth/v1/sub-enterprises` | Create sub-enterprise user |
| GET | `/sgod-auth/v1/sub-enterprises/deleted` | Get deleted sub-enterprise users |
| PATCH | `/sgod-auth/v1/sub-enterprises/me` | Update my profile (me alias) |
| PATCH | `/sgod-auth/v1/sub-enterprises/my-profile` | Update my profile |
| PATCH | `/sgod-auth/v1/sub-enterprises/profile` | Update my profile (alias) |
| GET | `/sgod-auth/v1/sub-enterprises/statistics` | Thống kê tổng quan Sub-Enterprise |
| DELETE | `/sgod-auth/v1/sub-enterprises/{userId}` | Delete sub-enterprise user |
| GET | `/sgod-auth/v1/sub-enterprises/{userId}` | Get sub-enterprise user profile |
| PATCH | `/sgod-auth/v1/sub-enterprises/{userId}` | Update sub-enterprise user |
| POST | `/sgod-auth/v1/sub-enterprises/{userId}/block` | Block sub-enterprise user |
| PATCH | `/sgod-auth/v1/sub-enterprises/{userId}/boss` | Set boss for sub-enterprise user |
| GET | `/sgod-auth/v1/sub-enterprises/{userId}/bosses` | Get available bosses for sub-enterprise user |
| POST | `/sgod-auth/v1/sub-enterprises/{userId}/organizational` | Assign department/position to sub-enterprise user |
| POST | `/sgod-auth/v1/sub-enterprises/{userId}/restore` | Restore sub-enterprise user |
| POST | `/sgod-auth/v1/sub-enterprises/{userId}/roles` | Assign roles to sub-enterprise user |
| POST | `/sgod-auth/v1/sub-enterprises/{userId}/unblock` | Unblock sub-enterprise user |

**sgod-auth-users-organizational**

| Method | Path | Summary |
|---|---|---|
| POST | `/sgod-auth/v1/users/{userId}/organizational/assign` | Assign department/position to user |
| GET | `/sgod-auth/v1/users/{userId}/organizational/bosses/available` | Get available bosses for user |
| POST | `/sgod-auth/v1/users/{userId}/organizational/bosses/set` | Set boss for user |
| GET | `/sgod-auth/v1/users/{userId}/organizational/check-subordinate` | Check if a subordinate is managed by a manager |
| POST | `/sgod-auth/v1/users/{userId}/organizational/remove` | Remove user from position |

</details>

<details><summary><b>asset-service</b> — 100 ops</summary>


**sgod-asset-categories**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/categories` | List categories flat (ListCategories) |
| POST | `/sgod-asset/v1/categories` | Create category (CreateCategory) |
| GET | `/sgod-asset/v1/categories/tree` | List categories as tree (ListCategoriesRecursive) |
| DELETE | `/sgod-asset/v1/categories/{id}` | Delete category (DeleteCategory) |
| GET | `/sgod-asset/v1/categories/{id}` | Get category by id (FindCategoryById) |
| PATCH | `/sgod-asset/v1/categories/{id}` | Update category (UpdateCategory) |

**sgod-asset-dashboard**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/dashboard/categories` | Dashboard category session stats (v1 parity) |
| GET | `/sgod-asset/v1/dashboard/es-stats` | ES aggregations — status distribution, monthly trend, top locations |
| GET | `/sgod-asset/v1/dashboard/fluctuations-asset` | Asset quantity fluctuation / cumulative (v1 parity) |
| GET | `/sgod-asset/v1/dashboard/statistics-asset` | Asset status time series (v1 parity) |
| GET | `/sgod-asset/v1/dashboard/summary` | Dashboard summary (GetDashboardSummary) |

**sgod-asset-import-export**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/import-export/exports` | List asset exports (ListAssetExports) |
| POST | `/sgod-asset/v1/import-export/exports` | Create asset export job (CreateAssetExport) |
| POST | `/sgod-asset/v1/import-export/exports/csv-download` | Export selected assets as CSV file (ExportAssetsCsv) |
| GET | `/sgod-asset/v1/import-export/exports/{exportId}` | Get asset export detail (GetAssetExport) |
| GET | `/sgod-asset/v1/import-export/import-templates` | Trả về danh sách trường CSV/Excel theo loại import — v1 GET /imports?subject=<type> |
| GET | `/sgod-asset/v1/import-export/import/batches/{importId}` | Get import batch detail (GetImportBatch) |
| POST | `/sgod-asset/v1/import-export/import/csv` | Import assets from CSV (ImportAssetsCsv) |
| POST | `/sgod-asset/v1/import-export/import/excel` | Import assets from Excel (ImportAssetsExcel) |

**sgod-asset-locations**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/locations` | List locations flat (ListLocations) |
| POST | `/sgod-asset/v1/locations` | Create location (CreateLocation) |
| GET | `/sgod-asset/v1/locations/tree` | List locations as tree (ListLocationsRecursive) |
| DELETE | `/sgod-asset/v1/locations/{id}` | Delete location (DeleteLocation) |
| GET | `/sgod-asset/v1/locations/{id}` | Get location by id (FindLocationById) |
| PATCH | `/sgod-asset/v1/locations/{id}` | Update location (UpdateLocation) |

**sgod-asset-maintenance**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/maintenance/records` | List records (ListMaintenanceRecords) |
| POST | `/sgod-asset/v1/maintenance/records` | Create record (CreateMaintenanceRecord) |
| DELETE | `/sgod-asset/v1/maintenance/records/{id}` | Xóa bản ghi bảo trì — DeleteMaintenanceRecord (đối chiếu v1 DELETE) |
| GET | `/sgod-asset/v1/maintenance/records/{id}` | Get record by id (FindMaintenanceRecordById) |
| PATCH | `/sgod-asset/v1/maintenance/records/{id}` | Update record (UpdateMaintenanceRecord) |
| GET | `/sgod-asset/v1/maintenance/schedules` | List maintenance schedules (ListMaintenanceSchedules) |
| POST | `/sgod-asset/v1/maintenance/schedules` | Create maintenance schedule (CreateMaintenanceSchedule) |
| GET | `/sgod-asset/v1/maintenance/schedules/count-by-tab` | Đếm lịch active / complete theo user — CountMaintenanceScheduleTabs (đối chiếu v1 count-by-tab) |
| DELETE | `/sgod-asset/v1/maintenance/schedules/{id}` | Xóa lịch và task/record liên quan — DeleteMaintenanceSchedule (đối chiếu v1 DELETE) |
| GET | `/sgod-asset/v1/maintenance/schedules/{id}` | Get schedule by id (FindMaintenanceScheduleById) |
| PATCH | `/sgod-asset/v1/maintenance/schedules/{id}` | Update schedule (UpdateMaintenanceSchedule) |
| GET | `/sgod-asset/v1/maintenance/schedules/{id}/block-chain` | Thông tin on-chain đã lưu — GetMaintenanceScheduleBlockchainInfo (đối chiếu v1 block-chain) |
| POST | `/sgod-asset/v1/maintenance/schedules/{id}/complete` | Complete schedule (CompleteMaintenanceSchedule) |
| GET | `/sgod-asset/v1/maintenance/schedules/{id}/get-by-id` | Chi tiết lịch — FindMaintenanceScheduleById (alias v1 get-by-id) |
| GET | `/sgod-asset/v1/maintenance/tasks` | List tasks (ListMaintenanceTasks) |
| POST | `/sgod-asset/v1/maintenance/tasks` | Create task (CreateMaintenanceTask) |
| GET | `/sgod-asset/v1/maintenance/tasks/{id}` | Get task by id (FindMaintenanceTaskById) |
| GET | `/sgod-asset/v1/maintenance/tasks/{id}/get-by-id` | Chi tiết task — FindMaintenanceTaskById (alias v1 get-by-id) |
| PATCH | `/sgod-asset/v1/maintenance/tasks/{id}/status` | Change task status (ChangeMaintenanceTaskStatus) |
| PATCH | `/sgod-asset/v1/maintenance/tasks/{id}/update-user` | Cập nhật staff/follower task — UpdateMaintenanceTaskUsers (alias v1 update-user) |
| PATCH | `/sgod-asset/v1/maintenance/tasks/{id}/users` | Update task users (UpdateMaintenanceTaskUsers) |
| GET | `/sgod-asset/v1/maintenance/tasks/{taskId}/discusses` | Danh sách bình luận của task — ListMaintenanceDiscusses |
| POST | `/sgod-asset/v1/maintenance/tasks/{taskId}/discusses` | Tạo bình luận trên maintenance task — CreateMaintenanceDiscuss |
| DELETE | `/sgod-asset/v1/maintenance/tasks/{taskId}/discusses/{discussId}` | Xóa bình luận (chỉ tác giả) — DeleteMaintenanceDiscuss |

**sgod-asset-offer**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/asset-offers` | Danh sách tên gợi ý tài sản — ListAssetsOffers |
| POST | `/sgod-asset/v1/asset-offers` | Tạo tên gợi ý cho tài sản — CreateAssetsOffer |
| DELETE | `/sgod-asset/v1/asset-offers/{id}` | Xóa tên gợi ý tài sản — DeleteAssetsOffer |
| GET | `/sgod-asset/v1/asset-offers/{id}` | Chi tiết tên gợi ý tài sản — FindAssetsOfferById |
| PATCH | `/sgod-asset/v1/asset-offers/{id}` | Cập nhật tên gợi ý tài sản — UpdateAssetsOffer |

**sgod-asset-report-template**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/report-templates` | Danh sách mẫu báo cáo — ListReportTemplates |
| POST | `/sgod-asset/v1/report-templates` | Tạo mẫu báo cáo — CreateReportTemplate |
| DELETE | `/sgod-asset/v1/report-templates/{id}` | Xóa mẫu báo cáo — DeleteReportTemplate |
| GET | `/sgod-asset/v1/report-templates/{id}` | Chi tiết mẫu báo cáo — FindReportTemplateById |
| PATCH | `/sgod-asset/v1/report-templates/{id}` | Cập nhật mẫu báo cáo — UpdateReportTemplate |

**sgod-asset-request-staff**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/request-staff` | Danh sách request staff — ListRequestStaff |
| POST | `/sgod-asset/v1/request-staff` | Tạo yêu cầu đổi trạng thái / bảo trì — CreateRequestStaffChangeStatus |
| POST | `/sgod-asset/v1/request-staff/change-location` | Yêu cầu đổi vị trí — CreateRequestStaffChangeLocation |
| GET | `/sgod-asset/v1/request-staff/summary` | Đếm tab gửi/nhận — CountRequestStaffTabs (parity v1) |
| GET | `/sgod-asset/v1/request-staff/{id}` | Chi tiết request staff — FindRequestStaffById |
| PATCH | `/sgod-asset/v1/request-staff/{id}` | Phê duyệt / từ chối — ApproveRequestStaff (parity v1 PATCH) |
| PATCH | `/sgod-asset/v1/request-staff/{id}/cancel` | Hủy yêu cầu — CancelRequestStaff |

**sgod-asset-status**

| Method | Path | Summary |
|---|---|---|
| POST | `/sgod-asset/v1/asset-statuses` | Create asset status session (CreateAssetStatus) |
| GET | `/sgod-asset/v1/asset-statuses/by-asset/{assetId}` | List statuses by asset id (ListAssetStatusesByAssetId) |
| GET | `/sgod-asset/v1/asset-statuses/history/{assetId}` | Lịch sử trạng thái tài sản — v1 GET /asset-statuses/:assetId/history |
| GET | `/sgod-asset/v1/asset-statuses/{id}` | Get asset status by id (FindAssetStatusById) |
| POST | `/sgod-asset/v1/asset-statuses/{id}/change-location` | Change location (ChangeAssetStatusLocation) |
| PATCH | `/sgod-asset/v1/asset-statuses/{id}/financials` | Update financial fields (UpdateAssetStatusFinancials) |
| POST | `/sgod-asset/v1/asset-statuses/{id}/revoke` | Revoke asset status session (RevokeAssetStatus) |
| POST | `/sgod-asset/v1/asset-statuses/{id}/separate` | Separate quantity (SeparateAssetStatus) |
| POST | `/sgod-asset/v1/asset-statuses/{id}/transition` | Transition asset status (TransitionAssetStatus) |

**sgod-asset-transfers**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/asset-transfers` | Danh sách phiếu chuyển giao tài sản — ListAssetTransfers |
| POST | `/sgod-asset/v1/asset-transfers` | Tạo phiếu chuyển giao tài sản — CreateAssetTransfer (yêu cầu bàn giao quantity từ phiên asset_status) |
| GET | `/sgod-asset/v1/asset-transfers/summary` | Đếm phiếu theo tab gửi / nhận / xác thực — CountAssetTransferTabs (đối chiếu v1 `count-items-of-tab`) |
| GET | `/sgod-asset/v1/asset-transfers/{id}` | Chi tiết phiếu chuyển giao tài sản — FindAssetTransferById |
| PATCH | `/sgod-asset/v1/asset-transfers/{id}` | Cập nhật phiếu chuyển giao tài sản — UpdateAssetTransfer |
| PATCH | `/sgod-asset/v1/asset-transfers/{id}/cancel` | Hủy phiếu chuyển giao tài sản — CancelAssetTransfer |
| PATCH | `/sgod-asset/v1/asset-transfers/{id}/delegated-staff` | Người nhận quyết định vai trò owner/manager — SetRecipientOwnerMode (đối chiếu v1 recipient-owner-mode) |
| PATCH | `/sgod-asset/v1/asset-transfers/{id}/respond` | Phản hồi phiếu chuyển giao (chấp nhận / từ chối) — RespondToAssetTransfer |

**sgod-assets**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/assets` | List assets (FindAllAssets) |
| POST | `/sgod-asset/v1/assets` | Create asset (asset.v1 CreateAsset) |
| GET | `/sgod-asset/v1/assets/histories/{historyId}` | Lấy chi tiết lịch sử thay đổi bằng ID — GetAssetHistoryById |
| GET | `/sgod-asset/v1/assets/suggest` | Gợi ý / autocomplete tên tài sản (search-as-you-type via Elasticsearch) |
| DELETE | `/sgod-asset/v1/assets/{id}` | Hard delete asset (HardDeleteAsset) |
| GET | `/sgod-asset/v1/assets/{id}` | Get asset by id (FindAssetById) |
| PATCH | `/sgod-asset/v1/assets/{id}` | Update asset (UpdateAsset) |
| PATCH | `/sgod-asset/v1/assets/{id}/add-location` | Thêm tài sản vào location mới kèm giá — v1 PATCH /assets/:id/add-location |
| GET | `/sgod-asset/v1/assets/{id}/blockchain` | Thông tin blockchain tài sản — v1 GET /asset-service/assets/:id/blockchain (Mongo + optional live RPC) |
| GET | `/sgod-asset/v1/assets/{id}/histories` | Lấy lịch sử thay đổi của tài sản — ListAssetHistories |
| PATCH | `/sgod-asset/v1/assets/{id}/restore` | Restore soft-deleted asset (RestoreAsset) |
| PATCH | `/sgod-asset/v1/assets/{id}/soft-delete` | Delete asset (DeleteAsset) |

**sgod-categories-offer**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-asset/v1/categories-offer` | Danh sách tên gợi ý danh mục — ListCategoriesOffers |
| POST | `/sgod-asset/v1/categories-offer` | Tạo tên gợi ý cho danh mục — CreateCategoriesOffer |
| DELETE | `/sgod-asset/v1/categories-offer/{id}` | Xóa tên gợi ý danh mục — DeleteCategoriesOffer |
| GET | `/sgod-asset/v1/categories-offer/{id}` | Chi tiết tên gợi ý danh mục — FindCategoriesOfferById |
| PATCH | `/sgod-asset/v1/categories-offer/{id}` | Cập nhật tên gợi ý danh mục — UpdateCategoriesOffer |

</details>

<details><summary><b>chat-service</b> — 62 ops</summary>


**Chat - Conversations**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/conversations` | Get conversations with pagination |
| POST | `/sgod-chat/v1/conversations/group` | Create a new group conversation |
| POST | `/sgod-chat/v1/conversations/private` | Get or create a private conversation |
| GET | `/sgod-chat/v1/conversations/unread-counts` | Get unread counts |
| GET | `/sgod-chat/v1/conversations/{id}` | Get conversation by ID |
| PATCH | `/sgod-chat/v1/conversations/{id}` | Update conversation |
| PATCH | `/sgod-chat/v1/conversations/{id}/disappearing` | Set disappearing messages |
| DELETE | `/sgod-chat/v1/conversations/{id}/disband` | Disband a conversation |
| POST | `/sgod-chat/v1/conversations/{id}/enable-e2ee` | Enable/Disable E2EE for conversation |
| POST | `/sgod-chat/v1/conversations/{id}/group-key` | Add group key for E2EE |
| POST | `/sgod-chat/v1/conversations/{id}/pinned-messages` | Pin message in conversation |
| DELETE | `/sgod-chat/v1/conversations/{id}/pinned-messages/{messageId}` | Unpin message in conversation |
| PATCH | `/sgod-chat/v1/conversations/{id}/settings` | Update conversation settings |
| POST | `/sgod-chat/v1/conversations/{id}/transfer-ownership` | Transfer conversation ownership |

**Chat - Drafts**

| Method | Path | Summary |
|---|---|---|
| DELETE | `/sgod-chat/v1/conversations/{conversationId}/drafts` | Clear message draft for a conversation |
| GET | `/sgod-chat/v1/conversations/{conversationId}/drafts` | Get message draft for a conversation |
| PUT | `/sgod-chat/v1/conversations/{conversationId}/drafts` | Save message draft for a conversation |

**Chat - Messages**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/messages` | Get messages by conversation |
| GET | `/sgod-chat/v1/messages/count-unread-message` | Count unread messages |
| GET | `/sgod-chat/v1/messages/search` | Search messages |
| GET | `/sgod-chat/v1/messages/{id}` | Get message by ID |

**Chat - Participants**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/conversations/{conversationId}/participants` | List all participants in conversation |
| POST | `/sgod-chat/v1/conversations/{conversationId}/participants` | Add members to conversation |
| DELETE | `/sgod-chat/v1/conversations/{conversationId}/participants/me` | Leave conversation (Self actions) |
| GET | `/sgod-chat/v1/conversations/{conversationId}/participants/me` | Get my participant in conversation |
| PATCH | `/sgod-chat/v1/conversations/{conversationId}/participants/me/archive` | Update Archive status |
| PATCH | `/sgod-chat/v1/conversations/{conversationId}/participants/me/auto-unarchive` | Update Auto-Unarchive status |
| POST | `/sgod-chat/v1/conversations/{conversationId}/participants/me/join` | Join conversation (Self actions) |
| PATCH | `/sgod-chat/v1/conversations/{conversationId}/participants/me/mute` | Update Mute status |
| PATCH | `/sgod-chat/v1/conversations/{conversationId}/participants/me/nickname` | Update my nickname or someone else nickname in this conversation |
| PATCH | `/sgod-chat/v1/conversations/{conversationId}/participants/me/pin` | Update Pin status |
| POST | `/sgod-chat/v1/conversations/{conversationId}/participants/me/public-key` | Add my public key for E2EE in this conversation |
| GET | `/sgod-chat/v1/conversations/{conversationId}/participants/members` | List all members in conversation (alias for participants, for @mention autocomplete) |
| DELETE | `/sgod-chat/v1/conversations/{conversationId}/participants/{targetUserId}` | Remove a specific member (Admin actions) |
| PATCH | `/sgod-chat/v1/conversations/{conversationId}/participants/{targetUserId}/role` | Update participant role |

**Chat - Poolings**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/poolings` | Get Poolings |
| GET | `/sgod-chat/v1/poolings/{id}` | Get Pooling by ID |
| GET | `/sgod-chat/v1/poolings/{id}/results` | Get Pooling Results |

**Chat - Reactions**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/reactions` | Get Reactions |
| GET | `/sgod-chat/v1/reactions/{messageId}` | Get My Reaction |

**Chat - Recipients**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/recipients` | Get user message states |
| GET | `/sgod-chat/v1/recipients/starred` | Get starred messages |
| POST | `/sgod-chat/v1/recipients/update` | Update user message state |

**Chat - Reports**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/reports` | List reports for moderation (tenant-scoped) |
| POST | `/sgod-chat/v1/reports` | Submit an abuse report |
| GET | `/sgod-chat/v1/reports/me` | List reports submitted by the current user |
| GET | `/sgod-chat/v1/reports/{reportId}` | Get a report by ID (tenant-scoped) |
| PATCH | `/sgod-chat/v1/reports/{reportId}/status` | Update report status (moderation) |

**Chat - Settings**

| Method | Path | Summary |
|---|---|---|
| DELETE | `/sgod-chat/v1/settings/current` | Delete Current User Setting |
| GET | `/sgod-chat/v1/settings/current` | Get Current User Setting |
| PATCH | `/sgod-chat/v1/settings/current` | Update Current User Setting |

**Chat - Sync**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/sync/delta` | Get chat delta updates |
| GET | `/sgod-chat/v1/sync/messages` | Sync messages for one conversation |
| GET | `/sgod-chat/v1/sync/snapshot` | Get initial chat snapshot |
| GET | `/sgod-chat/v1/sync/state` | Get message sync state for one conversation/device session |

**Chat - User Blocks**

| Method | Path | Summary |
|---|---|---|
| GET | `/sgod-chat/v1/user-blocks` | List blocked users |
| POST | `/sgod-chat/v1/user-blocks/block` | Block a user |
| GET | `/sgod-chat/v1/user-blocks/status` | Check block status |
| POST | `/sgod-chat/v1/user-blocks/unblock` | Unblock a user |

**health**

| Method | Path | Summary |
|---|---|---|
| GET | `/health` | Health check endpoint - Supports auth, chat, upload, notification, mailer, payment, proposal |
| GET | `/health/grpc` | Check gRPC connection health - Supports auth, chat, upload, notification, mailer, payment |
| GET | `/health/mailer` | Check notification-service mailer health |

</details>


---
*Generated from live Swagger specs + live API responses. SGOD @ 10.10.0.2:5007.*
