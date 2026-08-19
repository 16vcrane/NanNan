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

## DELETE /api/v1/users/me

Permanently deletes the authenticated account and all owned server data. The
service locks the user row, removes every owned private image object, then
deletes `UserProfile`; database foreign keys cascade to diaries, image records,
AI reflections, and timeline markers.

```json
{
  "code": 0,
  "message": "ok",
  "data": { "deleted": true }
}
```

If private storage cleanup fails, the account remains and the endpoint returns
`503 USER_DATA_DELETE_FAILED`, allowing the user to retry. Existing access
tokens no longer authenticate after successful deletion because the user row
no longer exists.

Phase 8 logout is client-side because access tokens are stateless. The client
removes its token, cached user, and unsaved local draft; it does not call the
account deletion endpoint. A later explicit login obtains a new token for the
same account.

## POST /api/v1/diaries

Creates a private diary entry for the authenticated user. The same transaction
creates its AI reflection state and up to three rule-based timeline markers;
AI generation begins after the diary transaction commits.

Request:

```json
{
  "content": "今天完成了数据库作业。",
  "energyScore": 65,
  "moodLabel": "愉悦",
  "imageIds": []
}
```

Constraints: `content` is 1–3000 characters, `energyScore` is 0–100, and
`imageIds` contains at most three unique image UUIDs. Every image must have
been uploaded successfully by the authenticated user and must not already be
attached to another diary. Invalid or foreign image IDs return
`400 DIARY_IMAGE_INVALID`.

Response `201`:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "diaryId": "uuid",
    "reflectionStatus": "pending"
  }
}
```

## GET /api/v1/diaries?page=1&limit=20

Returns only the authenticated user's non-deleted entries, ordered by
`createdAt DESC`. `limit` is between 1 and 100.

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": "uuid",
        "content": "今天完成了数据库作业。",
        "energyScore": 65,
        "moodLabel": "愉悦",
        "privacyStatus": "private",
        "createdAt": "2026-08-15T08:00:00Z",
        "updatedAt": "2026-08-15T08:00:00Z",
        "images": [
          {
            "id": "uuid",
            "status": "success",
            "url": "/api/v1/uploads/images/uuid/content",
            "contentType": "image/jpeg",
            "sizeBytes": 12345,
            "sortOrder": 0
          }
        ],
        "markers": [
          {
            "id": "uuid",
            "type": "growth",
            "keyword": "完成",
            "displayText": "完成",
            "color": "#789184",
            "sortOrder": 0
          }
        ]
      }
    ],
    "page": 1,
    "limit": 20,
    "hasMore": false
  }
}
```

## GET /api/v1/diaries/{diaryId}

Returns a diary only when both `diaryId` and the authenticated user's ID match.
`images` contains the diary's successful images in `sortOrder`; `reflection`
contains its current AI state; `markers` uses the same marker object returned
by the list endpoint.

## GET /api/v1/memories/on-this-day

Returns up to three records owned by the authenticated user for a local
calendar-day recall. The query accepts an IANA timezone name:

```http
GET /api/v1/memories/on-this-day?timezone=Asia/Shanghai
```

Candidates are ordered by: same month/day in prior years, then 30, 100, and
365 days ago. Deleted and foreign diaries are excluded. The response contains
only a normalized short text summary, date, and mood metadata; it does not
expose images in this entry point. When no recall exists, `items` is an empty
array.

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "today": "2026-08-19",
    "timezone": "Asia/Shanghai",
    "items": [
      {
        "diaryId": "uuid",
        "date": "2025-08-19",
        "createdAt": "2025-08-19T08:00:00Z",
        "energyScore": 65,
        "moodLabel": "愉悦",
        "summary": "今天完成了数据库作业。",
        "source": "same_date",
        "distanceDays": 365
      }
    ]
  }
}
```

An invalid timezone returns `400 TIMEZONE_INVALID`.

## PATCH /api/v1/users/me/ai-preferences

Controls whether the user's future AI reflections may use structured personal
memory. It defaults to `false`; disabling it immediately returns future
reflections to the current-diary-only prompt. Existing diary text is never
changed.

```http
PATCH /api/v1/users/me/ai-preferences
Content-Type: application/json

{"personalMemoryEnabled": true}
```

The response contains the saved `personalMemoryEnabled` value. Retrieval audit
records contain only IDs and counts, never diary or evidence text.

## DELETE /api/v1/diaries/{diaryId}

Soft-deletes an owned diary. Deleted entries are excluded from list and detail
queries. The response is:

```json
{
  "code": 0,
  "message": "ok",
  "data": { "deleted": true }
}
```

Unknown, deleted, or foreign diary IDs return `404 DIARY_NOT_FOUND`.
Deleting a diary also deletes its stored image objects and soft-deletes its
image records. A storage failure returns `503 DIARY_DELETE_FAILED` and leaves
the diary active so the operation can be retried.

## POST /api/v1/uploads/images

Uploads one authenticated user's image as `multipart/form-data` using the
field name `file`. The server accepts at most 10 MB, verifies the content with
Pillow, applies EXIF orientation, limits the longest side to 2048 pixels, and
stores a metadata-clean JPEG in private storage.

Response `201`:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "uuid",
    "status": "success",
    "url": "/api/v1/uploads/images/uuid/content",
    "contentType": "image/jpeg",
    "sizeBytes": 12345,
    "sortOrder": 0
  }
}
```

Errors:

| Status | Code | Meaning |
| --- | --- | --- |
| `422` | `IMAGE_INVALID` | File is empty, over 10 MB, or not a valid image. |
| `503` | `IMAGE_UPLOAD_FAILED` | Private object storage could not persist the image. |

## GET /api/v1/uploads/images/{imageId}/content

Returns the JPEG bytes only to the owning authenticated user. Missing,
deleted, failed, or foreign images return `404 IMAGE_NOT_FOUND`. The endpoint
exists because image objects are private and must not be exposed by public
storage URLs.

## DELETE /api/v1/uploads/images/{imageId}

Deletes an uploaded image that has not yet been attached to a diary. Foreign
or missing IDs return `404 IMAGE_NOT_FOUND`; attached images return
`409 IMAGE_ALREADY_ATTACHED`; storage failures return
`503 IMAGE_DELETE_FAILED`.

# Phase 5：AI 回响

所有接口均要求 `Authorization: Bearer <token>`，且仅返回当前用户未删除日记的回响。

## 查询回响

```http
GET /api/v1/diaries/{diaryId}/reflection
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "uuid",
    "diaryId": "uuid",
    "status": "pending|success|failed|blocked",
    "content": "string|null",
    "safetyStatus": "safe|sensitive|blocked",
    "canRetry": false,
    "attemptCount": 1
  }
}
```

日记不存在、不属于当前用户或已经软删除时返回 `REFLECTION_NOT_FOUND`（404）。

## 重试回响

```http
POST /api/v1/diaries/{diaryId}/reflection/retry
```

成功返回 202，后台重新生成：

```json
{
  "code": 0,
  "message": "ok",
  "data": { "status": "pending", "attemptCount": 1 }
}
```

仅 `failed` 且未达到最大尝试次数时允许重试，否则返回 `REFLECTION_RETRY_NOT_ALLOWED`（409）。

# Phase 6：关键词与关键帧

关键帧随日记创建，不提供客户端写入接口。服务端使用集中词库按关键词在正文中的首次出现位置排序、去重并最多保存 3 个标签。无命中时 `markers` 返回空数组。

当前类型为 `growth | relationship | place | achievement | custom`。列表和详情接口都按 `sortOrder` 返回标签；任何查询均同时校验当前用户。删除日记时同步删除关联关键帧。

# Phase 7：时间轴与详情

时间轴复用 `GET /api/v1/diaries?page={page}&limit={limit}`。`page` 从 1 开始，`limit` 范围为 1 至 100，默认 20；响应中的 `hasMore` 决定客户端是否继续请求下一页。服务端按 `createdAt DESC, id DESC` 稳定排序，并批量加载当前页的图片和关键帧。

列表图片只返回需要鉴权的私有内容 URL，小程序必须携带登录态下载后再显示，不得拼接公开对象存储地址。

点击列表卡片后调用 `GET /api/v1/diaries/{diaryId}`。详情返回完整原文、全部成功图片、AI 回响和关键帧。删除使用 `DELETE /api/v1/diaries/{diaryId}`，客户端必须二次确认；成功后返回时间轴并刷新第一页。

# Phase 9：工程质量契约

所有响应都包含 `X-Request-ID`。客户端可以传入不超过 128 字符的
`X-Request-ID` 以便关联日志，否则服务端生成 UUID。日志只记录请求方法、路径、
状态码、耗时和必要业务标识，不记录 token、日记正文或图片内容。

参数验证错误统一返回：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数不符合要求",
  "data": { "fields": ["content"] }
}
```

未处理异常返回 `500 INTERNAL_ERROR`，不向客户端暴露堆栈或内部依赖信息。

API 使用 Redis 固定窗口限流。超过限制返回 `429 RATE_LIMITED`，并通过
`Retry-After` 响应头告知建议等待秒数。Redis 暂时不可用时限流降级为放行，
核心记录流程不因此中断。

创建日记支持 `X-Idempotency-Key`，长度为 8 至 128 字符。同一用户使用相同键：

- 首次请求正常创建日记；
- 首次请求仍在处理时返回 `409 DUPLICATE_SUBMISSION`；
- 首次请求已完成时返回原有 `diaryId`，不会再次创建日记或 AI 回响任务。

幂等键按用户隔离。小程序在一次保存及网络重试期间复用同一个键，内容发生修改后
生成新键。
