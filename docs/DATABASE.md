# Database Schema

## Migration workflow

Alembic migrations live in `backend/migrations/versions`. The backend container
runs `alembic upgrade head` before starting FastAPI.

Current revision: `20260815_0001`.

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
