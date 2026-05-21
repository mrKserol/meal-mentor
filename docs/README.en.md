# Meal Mentor — documentation (EN)

[Русский](README.ru.md) · [Root README](../README.md) · [Architecture](architecture.md)

A nutrition tracking service: **web app**, **Telegram bot**, and **REST API** on FastAPI. Users log meals, track calories and macros, set goals, and unlock paid-plan features. Admins manage users, plans, and subscriptions.

---

## Table of contents

1. [Product features](#product-features)
2. [Repository layout](#repository-layout)
3. [Authentication](#authentication)
4. [Plans, limits, and entitlements](#plans-limits-and-entitlements)
5. [Web UI](#web-ui)
6. [Telegram bot](#telegram-bot)
7. [Admin panel](#admin-panel)
8. [Database](#database)
9. [Environment variables](#environment-variables)
10. [Running and deployment](#running-and-deployment)
11. [Migrations and scripts](#migrations-and-scripts)
12. [API](#api)
13. [Tests](#tests)

---

## Product features

### Web

- **Sign-in:** email/password, **Telegram OAuth**, **Yandex OAuth** (profile: email, name, sex and birth date when OAuth scopes allow).
- **Dashboard:** greeting and today’s diary card vs daily macro targets from the DB.
- **Diary:** week/month stats, meal history, weight, daily targets; add meals for past dates (not today).
- **Profile:** sex, age, height, weight, goal, activity, allergens (if enabled by plan), Mifflin–St Jeor macro targets.
- **Add meal:** photo / file / text → AI analysis → confirm composition and weights → save; edit title and ingredients with macro recalc without another AI call.
- **Label analysis:** upload a product label photo (separate prompt).
- **PWA:** install to home screen (`manifest`, service worker, icons).

### Telegram

- Photo → analysis → confirmation → save by `telegram_id`.
- Text flow when vision confidence is low.
- Reports and flows using existing report endpoints.

### Data core

- Normalized meals: `meals` → `meal_items` → `meal_item_nutrition`.
- Active **macro target** per user (`nutrition_targets`).
- Diary snapshot for UI: `diary_snapshot` (week, month, today, recent meals, weight).
- Ingredient matching to CSV with aliases, food state (dry/cooked/fried), categories, and regression fixtures.

---

## Repository layout

```
meal-mentor/
├── frontend/                 # React + Vite + TypeScript + Tailwind (main UI)
│   ├── public/               # PWA assets
│   └── src/
│       ├── pages/            # Login, Dashboard, Diary, Profile, Admin, OAuth callbacks
│       ├── components/       # AppShell, AddMealModal, EditMealModal, admin UI
│       ├── api/              # authApi, diaryApi, mealsApi, adminApi
│       └── admin/            # feature key presets for plans
├── app/
│   ├── core/                 # use cases (meal_analysis, …)
│   ├── infrastructure/       # OpenAI, nutrition CSV, storage
│   ├── interfaces/
│   │   ├── api/              # /users, /meals, /reports, /subscriptions (bot)
│   │   └── telegram/         # long-polling bot
│   ├── routers/
│   │   ├── auth.py           # JWT, OAuth
│   │   ├── users.py          # /users/me/* (web JWT)
│   │   └── admin.py          # /admin/* (admin role)
│   ├── services/             # diary_snapshot, nutrition_targets, feature_access, usage_limits
│   ├── auth/                 # JWT, OAuth providers
│   └── db/                   # models, repository, session
├── alembic/                  # DB migrations
├── data/                     # nutrition.csv, food_aliases.json, prompts
├── scripts/                  # backfill_auth_identities.py, …
├── tests/
├── docs/
├── service.py                # uvicorn entry: service:app
└── requirements.txt
```

Layer details: [architecture.md](architecture.md).

---

## Authentication

- **JWT:** `access_token` + `refresh_token`; payload uses internal `users.id` (stable when linking OAuth).
- **Identities:** `user_auth_identities` (`provider`, `provider_user_id`). Legacy Telegram users keep `users.telegram_id`; login creates/finds a `telegram` identity.
- **Web providers:** Telegram OIDC, Yandex OAuth.
- **Registration:** email + password with profile fields.

Backfill existing Telegram users:

```bash
python -m scripts.backfill_auth_identities
```

---

## Plans, limits, and entitlements

### Models

- `plans` + `plan_features` — plan and feature set (boolean / limit).
- `subscriptions` — user’s active plan.
- `user_feature_overrides` — manual overrides (admin).
- `feature_usage` — AI usage counters (daily / monthly periods).

### Feature keys

| Boolean | Limit |
|---------|-------|
| `nutrition_diary_enabled` | `daily_ai_requests_limit` |
| `advanced_nutrients_enabled` | `daily_ai_chat_messages_limit` |
| `food_photo_recognition_enabled` | `daily_photo_recognition_limit` |
| `label_analysis_enabled` | `monthly_photo_recognition_limit` |
| `ai_chat_enabled` | `monthly_label_analysis_limit` |
| `allergens_enabled` | |

Limit `-1` = unlimited. Limit `0` = disabled. Counters increment after a **successful** AI call; multiple counters per request are updated **atomically** (`increment_many_usage` in `app/services/usage_limits.py`).

### Web AI checks

- Photo: `food_photo_recognition_enabled` + daily/monthly photo limits + `daily_ai_requests_limit`.
- Label: `label_analysis_enabled` + `monthly_label_analysis_limit` + daily AI limit.
- Text-only: `daily_ai_requests_limit` only.

JWT endpoints with limits: `POST /users/me/meals/analyze`, `analyze-text`, `analyze-image-text`, `POST /users/me/analyze-label`.

Public `POST /meals/analyze*` (no JWT) is for the bot and does not apply web limits.

`GET /users/me/entitlements` — current plan and feature map for the UI.

Plan feature seeding: migration `018_seed_plan_features_v2` (`free`, `basic_month`, `pro_month`).

---

## Web UI

| Route | Page |
|-------|------|
| `/login` | Sign in (Telegram / Yandex) |
| `/register` | Registration |
| `/auth/telegram/callback`, `/auth/yandex/callback` | OAuth callbacks |
| `/dashboard` | Home |
| `/diary` | Diary |
| `/onboarding/profile` | Profile and macro goals |
| `/admin` | Admin (role `admin`) |

**AppShell:** sidebar, header, mobile FAB “+”, add/edit meal and label modals.

**Add meal:** `POST /users/me/meals/analyze*` → confirm → `POST /users/me/meals/save` (optional `meal_local_date` for past days).

**Edit meal:** `PATCH /users/me/meals/{id}`, delete via `DELETE`.

---

## Telegram bot

```bash
python -m app.bot.telegram_bot
```

Requires `TELEGRAM_BOT_TOKEN` and API reachable at `BASE_URL`. The bot calls public `/meals/*` endpoints and saves by `telegram_id`.

---

## Admin panel

Access: `role=admin` (bootstrap via `ADMIN_BOOTSTRAP_EMAILS` on first email login).

Sections:

- **Users** — search, provider (from identities), role, status, subscription; swipe-to-delete with confirmation; grant subscription; feature overrides.
- **Plans** — create/edit plans and features (boolean/limit labels); delete plan (deactivates if subscriptions exist).
- **Subscriptions** — list and cancel.

API prefix: `/admin`, Bearer JWT.

---

## Database

| Table | Purpose |
|-------|---------|
| `users` | Profile, role, status, `telegram_id` (legacy, keep) |
| `user_auth_identities` | OAuth / telegram / email links |
| `meals`, `meal_items`, `meal_item_nutrition` | Meals and macros |
| `nutrition_targets` | Daily macro targets |
| `allergens` | User allergens |
| `user_measurements` | Weight and measurements |
| `plans`, `plan_features` | Plans |
| `subscriptions` | Subscriptions |
| `user_feature_overrides` | Manual entitlements |
| `feature_usage` | AI usage counters |
| `refresh_tokens` | JWT refresh |
| `daily_summary`, `recommendations_log` | Summaries / recommendations |

Default: SQLite (`DATABASE_URL`); production: PostgreSQL recommended.

---

## Environment variables

### Backend (`.env.example`)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI for photo/text/labels |
| `PROMPT_PATH`, `PROMPT2_PATH` | Prompts (`data/promt.txt`, `promt2.txt`) |
| `NUTRITION_CSV_PATH`, `FOOD_ALIASES_PATH` | Nutrition DB and aliases |
| `LOW_CONFIDENCE_THRESHOLD` | Text fallback threshold (default `0.5`) |
| `NUTRITION_DEBUG_MATCHING` | Verbose matching logs |
| `NUTRITION_ENABLE_SEMANTIC` | Semantic search (heavy; off by default) |
| `DATABASE_URL` | SQLAlchemy URL |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM` | JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | Token TTL |
| `TELEGRAM_BOT_TOKEN`, `BASE_URL` | Bot |
| `TELEGRAM_CLIENT_ID`, `TELEGRAM_CLIENT_SECRET`, `TELEGRAM_REDIRECT_URI` | Telegram OAuth (backend) |
| `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI` | Yandex OAuth (backend) |
| `ADMIN_BOOTSTRAP_EMAILS` | Comma-separated emails → admin on login |
| `MEAL_PHOTO_UPLOAD_DIR` | On-disk meal photos |
| `SUBSCRIPTION_DEMO_AUTO` | Demo subscription without payment |

### Frontend (`frontend/.env.example`)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | FastAPI base URL |
| `VITE_TELEGRAM_CLIENT_ID`, `VITE_TELEGRAM_REDIRECT_URI` | Telegram OAuth |
| `VITE_YANDEX_CLIENT_ID`, `VITE_YANDEX_REDIRECT_URI` | Yandex OAuth |
| `VITE_YANDEX_SCOPES` | e.g. `login:info login:email login:avatar login:birthday` |

---

## Running and deployment

### Backend

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn service:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev          # http://localhost:5173
npm run build        # dist/
npm run preview
```

### Telegram bot

```bash
python -m app.bot.telegram_bot
```

### Production (brief)

- API: Railway / Docker + `uvicorn service:app`.
- Frontend: static `frontend/dist` from `npm run build`.
- CORS is permissive (`*`); tighten origins if needed.
- Rotate `JWT_SECRET_KEY` and OAuth secrets.

---

## Migrations and scripts

```bash
alembic upgrade head
```

Notable revisions: `016_user_auth_identities`, `017_feature_usage`, `018_seed_plan_features_v2`.

```bash
python -m scripts.backfill_auth_identities
```

Creates `user_auth_identities` for users with `telegram_id` (does not change `users.id`).

---

## API

### Auth — `/auth`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Register |
| POST | `/login` | Email + password |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Revoke refresh token |
| POST | `/telegram/callback` | Telegram OAuth (web) |
| POST | `/yandex/callback` | Yandex OAuth |

### Web user — `/users` (Bearer)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/me` | Profile + targets + allergens |
| PATCH | `/me/profile` | Update profile |
| GET | `/me/entitlements` | Plan and features |
| GET | `/me/diary` | Diary snapshot |
| GET | `/me/meals/day?date=YYYY-MM-DD` | Meals for a day |
| POST | `/me/meals/analyze` | Photo analysis (limits) |
| POST | `/me/meals/analyze-text` | Text analysis |
| POST | `/me/meals/analyze-image-text` | Photo + text correction |
| POST | `/me/meals/save` | Save meal |
| PATCH | `/me/meals/{meal_id}` | Edit meal |
| DELETE | `/me/meals/{meal_id}` | Delete meal |
| POST | `/me/analyze-label` | Label analysis (multipart) |
| GET/POST | `/me/measurements` | Weight / measurements |
| GET | `/me/nutrition-target` | Active macro target |

### Meals (bot) — `/meals`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/analyze` | Base64 photo (no web limits) |
| POST | `/analyze-text` | Text |
| POST | `/analyze-image-text` | Photo + text |
| POST | `/recalculate` | Macros from ingredients without AI |
| POST | `/save` | Save by `telegram_id` |

### Admin — `/admin` (Bearer, admin role)

Users, plans, features, subscriptions, overrides — see OpenAPI or `app/routers/admin.py`.

---

## Tests

```bash
pytest
```

Focused:

```bash
pytest tests/test_nutrition_matching.py
pytest tests/test_usage_limits.py
pytest tests/test_feature_access.py
```

**Nutrition matching:** fixtures in `tests/fixtures/nutrition_matching_cases.json`. Add cases when fixing matcher bugs. Verbose logs: `NUTRITION_DEBUG_MATCHING=1`.

**Usage limits:** atomic multi-counter increment per AI request.

---

## See also

- [architecture.md](architecture.md) — Telegram / API / core flows
- [frontend/README.md](../frontend/README.md) — npm scripts and `VITE_*`
