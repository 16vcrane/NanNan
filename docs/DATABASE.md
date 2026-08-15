# Database Schema

## Migration workflow

Alembic migrations live in `backend/migrations/versions`. The backend container
runs `alembic upgrade head` before starting FastAPI.

Current revision: `20260815_0004`.

## user_profiles

Stores the minimum stable identity and user settings required by the MVP.
WeChat session keys and unnecessary profile data are not persisted.

| Column | Type | Constraints / Default |
| --- | --- | --- |
| `id` | `UUID` | Primary key |
| `wechat_open_id` | `VARCHAR(64)` | Unique, not null |
| `created_at` | `TIMESTAMPTZ` | Not null, `now()` |
| `last_active_at` | `TIMESTAMPTZ` | Not null, `now()` |
| `ai_reflection_enabled` | `BOOLEAN` | Not null, `true` |
| `anniversary_reminder_enabled` | `BOOLEAN` | Not null, `false` |
| `third_person_unlocked` | `BOOLEAN` | Not null, `false` |

Login uses a PostgreSQL upsert on `wechat_open_id`, which prevents duplicate
users during concurrent or repeated login attempts and updates `last_active_at`.

## diary_entries

All diary access is scoped by `user_id`; application queries also exclude rows
where `deleted_at` is set.

| Column | Type | Constraints / Default |
| --- | --- | --- |
| `id` | `UUID` | Primary key |
| `user_id` | `UUID` | Foreign key to `user_profiles.id`, not null |
| `content` | `TEXT` | Not null; API accepts 1–3000 characters |
| `energy_score` | `INTEGER` | Not null, API range 0–100, default 50 |
| `mood_label` | `VARCHAR(32)` | Nullable |
| `privacy_status` | `VARCHAR(16)` | Not null, default `private` |
| `ai_reflection_id` | `UUID` | Nullable foreign key to `ai_reflections.id`; delete sets null |
| `created_at` | `TIMESTAMPTZ` | Not null, `now()` |
| `updated_at` | `TIMESTAMPTZ` | Not null, `now()` |
| `deleted_at` | `TIMESTAMPTZ` | Nullable soft-delete marker |

Indexes:

- `diary_entries(user_id, created_at)` for timeline ordering.
- `diary_entries(user_id, deleted_at)` for active-entry filtering.

## diary_images

Tracks private image objects before and after they are attached to a diary.
Upload and diary ownership checks always scope records by `user_id`. Deleting
an image or diary sets `deleted_at`; the corresponding object is removed from
private storage.

| Column | Type | Constraints / Default |
| --- | --- | --- |
| `id` | `UUID` | Primary key |
| `diary_id` | `UUID` | Nullable foreign key to `diary_entries.id`, `ON DELETE CASCADE` |
| `user_id` | `UUID` | Foreign key to `user_profiles.id`, not null, `ON DELETE CASCADE` |
| `storage_key` | `VARCHAR(255)` | Unique, not null; private object key |
| `url` | `VARCHAR(255)` | Authenticated content endpoint, not null |
| `content_type` | `VARCHAR(64)` | Not null, default `image/jpeg` |
| `size_bytes` | `INTEGER` | Normalized object size, not null |
| `sort_order` | `INTEGER` | Order inside a diary, not null, default 0 |
| `status` | `VARCHAR(24)` | `uploading`, `success`, `failed`, or `deleted` |
| `created_at` | `TIMESTAMPTZ` | Not null, `now()` |
| `deleted_at` | `TIMESTAMPTZ` | Nullable soft-delete marker |

Indexes:

- `diary_images(diary_id)` for diary detail and deletion cleanup.
- `diary_images(user_id, status)` for owned upload lookups.

# Phase 5：AI 回响

## ai_reflections

| 字段 | 类型 | 约束/说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| diary_entry_id | UUID | `diary_entries.id`，唯一，级联删除 |
| user_id | UUID | `user_profiles.id`，级联删除 |
| status | varchar(16) | `pending/success/failed/blocked` |
| content | text | 仅保存校验后的回响或固定兜底文案 |
| model_name | varchar(128) | 实际模型名，可空 |
| prompt_version | varchar(32) | 当前为 `reflection_v1` |
| safety_status | varchar(16) | `safe/sensitive/blocked` |
| attempt_count | integer | 已执行生成次数，默认 0 |
| error_code | varchar(64) | 安全的内部错误分类，可空 |
| latency_ms | integer | 生成耗时，可空 |
| token_usage | integer | Provider 返回的总 token，可空 |
| created_at / updated_at | timestamptz | 创建和更新时间 |

索引：`diary_entry_id`、`(user_id, status)`。`diary_entries.ai_reflection_id` 增加到 `ai_reflections.id` 的外键，删除回响时置空。

迁移：`20260815_0004_create_ai_reflections.py`。
