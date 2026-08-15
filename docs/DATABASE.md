# Database Schema

## Migration workflow

Alembic migrations live in `backend/migrations/versions`. The backend container
runs `alembic upgrade head` before starting FastAPI.

Current revision: `20260815_0003`.

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
| `ai_reflection_id` | `UUID` | Nullable placeholder for Phase 5 |
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
