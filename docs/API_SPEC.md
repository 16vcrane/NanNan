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
