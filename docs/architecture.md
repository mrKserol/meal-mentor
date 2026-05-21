# Meal Mentor — architecture (core + interfaces)

[Русская документация](README.ru.md) · [English](README.en.md)

## Goal

One **nutrition AI core** (analyze meal → normalize → CSV lookup → persist) with **multiple UI adapters**: **React web** (JWT, plans, limits), **Telegram** (public `/meals/*`), and room for MAX / mobile later.

## Layout

```
app/
├── core/                    # Domain-oriented: config, prompts, shared schemas, use cases
│   ├── config.py
│   ├── prompts.py
│   ├── schemas.py           # MealAnalysisResult, MealLogRequest, MacroTotals, …
│   └── use_cases/
│       └── meal_analysis.py # analyze_meal_from_image_base64, persist_meal_to_database, …
├── infrastructure/          # External I/O (no Telegram / FastAPI)
│   ├── ai/
│   │   └── openai_food_client.py   # OpenAI vision + text
│   └── nutrition/
│       └── csv_nutrition_provider.py  # nutrition.csv + fuzzy/semantic
├── db/                      # SQLAlchemy models, session, repository
├── services/                # diary_snapshot, nutrition_targets, feature_access, usage_limits, …
├── auth/                    # JWT, OAuth (Telegram, Yandex), user_auth_identities
├── routers/                 # auth, users (/users/me/*), admin
├── interfaces/              # Transport / UI
│   ├── api/                 # FastAPI routers (/meals, /reports, /subscriptions)
│   ├── telegram/            # Long-polling bot, handlers, FSM state
│   └── max/                 # Placeholder for MAX messenger
├── api/                     # Shims re-exporting interfaces.api (stable imports)
├── bot/                     # Shims re-exporting interfaces.telegram (python -m app.bot.telegram_bot)
└── main.py                  # FastAPI app assembly + CORS
```

**Web UI** lives in `frontend/` (React + Vite), not in `app/interfaces/web/`.

## Flow: Telegram → API → core

1. User sends a photo in Telegram.
2. `interfaces/telegram` downloads the file, encodes base64, calls **`POST /meals/analyze`** on the API (HTTP).
3. `interfaces/api/routes_meals` calls **`core/use_cases/meal_analysis.analyze_meal_from_image_base64`**.
4. Use case uses **`infrastructure/ai`** (vision) then **`infrastructure/nutrition`** (CSV) and returns **`MealAnalysisResult`** → serialized with **`to_api_dict()`** (legacy JSON shape).
5. User confirms → **`POST /meals/save`** → **`persist_meal_to_database`** → **`db/repository`**.

Telegram does **not** import core directly in this deployment; the HTTP boundary matches a split setup (bot process + API process). Public meal endpoints do not apply web usage limits.

## Flow: Web (React) → API → core

1. User uploads photo/text in **`AddMealModal`** (authenticated).
2. Frontend calls **`POST /users/me/meals/analyze*`** with Bearer JWT.
3. **`app/routers/users.py`** checks entitlements and usage limits (`feature_access`, `usage_limits`), then runs the same use cases as `/meals/*`.
4. On success, usage counters increment atomically; user confirms → **`POST /users/me/meals/save`** with `user_id` from JWT.

OAuth (Telegram / Yandex) goes through **`/auth/*/callback`** → **`user_auth_identities`**; JWT still references **`users.id`**.

## Adding a new channel (e.g. MAX)

1. Add `app/interfaces/max/` with handlers analogous to Telegram: parse user input, build base64 or text, call **`/meals/analyze`** or **`/meals/analyze-text`**, then **`/meals/save`** with a stable user id (today `telegram_id` in bot payloads).
2. Keep keyboards and callback strings **inside** the MAX package, not in `core/`.
3. Reuse **`MealAnalysisResult`** / **`MealLogRequest`** if you call Python use cases in-process instead of HTTP.

## Compatibility shims

- **`app.services.openai_vision`** / **`app.services.nutrition_service`** re-export **`infrastructure`** implementations.
- **`app.api.routes_*`** re-export routers from **`app.interfaces.api`**.
- **`app.bot.*`** re-export **`app.interfaces.telegram.*`** so existing commands and imports keep working.

## Environment & deploy

- API: `uvicorn service:app`
- Web dev: `cd frontend && npm run dev`
- Bot: `python -m app.bot.telegram_bot`

Same env vars: `OPENAI_API_KEY`, `BASE_URL`, `DATABASE_URL`, JWT and OAuth secrets — see [README.ru.md](README.ru.md) or [README.en.md](README.en.md).
