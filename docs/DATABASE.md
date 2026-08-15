# Database Schema

## Migration workflow

Alembic migrations live in `backend/migrations/versions`. The backend container
runs `alembic upgrade head` before starting FastAPI.

Current revision: `20260815_0002`.

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
