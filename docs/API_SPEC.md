# API Specification

## Conventions

- Base path: `/api/v1`
- Content type: `application/json`
- Authenticated endpoints use `Authorization: Bearer <access-token>`.
- Secrets, WeChat `session_key`, and `openid` are never returned to the client.
- `JWT_SECRET` must contain at least 32 characters.

Successful responses use:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Authentication errors use:

```json
{
  "code": "AUTH_INVALID",
  "message": "登录状态无效或已过期",
  "data": null
}
```

## POST /api/v1/auth/login

Exchanges a temporary `wx.login` code for the application's access token. A new
`UserProfile` is created on first login; later logins reuse the same user.

Request:

```json
{
  "code": "wechat-login-code"
}
```

Response `200`:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "accessToken": "jwt",
    "user": {
      "id": "uuid",
      "createdAt": "2026-08-15T00:00:00Z",
      "lastActiveAt": "2026-08-15T00:00:00Z",
      "settings": {
        "aiReflectionEnabled": true,
        "anniversaryReminderEnabled": false,
        "thirdPersonUnlocked": false
      }
    }
  }
}
```

Errors:

| Status | Code | Meaning |
| --- | --- | --- |
| `401` | `AUTH_INVALID` | WeChat code or access token is invalid. |
| `502` | `AUTH_UPSTREAM_ERROR` | WeChat service is unavailable or returned an invalid response. |
| `503` | `AUTH_NOT_CONFIGURED` | Required WeChat or JWT configuration is missing. |

## GET /api/v1/users/me

Returns the user identified by the bearer token. The endpoint does not accept a
client-provided user ID.

Response `200` uses the same user object returned by the login endpoint.

Response `401`: `AUTH_INVALID`.
