# Meal Mentor — architecture (core + interfaces)

## Goal

One **nutrition AI core** (analyze meal → normalize → CSV lookup → persist) with **multiple UI adapters** (Telegram today; MAX / web / mobile later).

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
├── db/                      # SQLAlchemy models, session, repository (future: infrastructure/db)
├── services/                # Facades & reporting (meal_service → use cases; report_service, …)
├── interfaces/              # Transport / UI
│   ├── api/                 # FastAPI routers (/users, /meals, /reports)
│   ├── telegram/            # Long-polling bot, handlers, FSM state
│   ├── max/                 # Placeholder for MAX messenger
│   └── web/                 # Notes; Streamlit demo is ../ui.py at repo root
├── api/                     # Shims re-exporting interfaces.api (stable imports)
├── bot/                     # Shims re-exporting interfaces.telegram (python -m app.bot.telegram_bot)
└── main.py                  # FastAPI app + legacy POST /generate_response
```

## Flow: Telegram → API → core

1. User sends a photo in Telegram.
2. `interfaces/telegram` downloads the file, encodes base64, calls **`POST /meals/analyze`** on the API (HTTP).
3. `interfaces/api/routes_meals` calls **`core/use_cases/meal_analysis.analyze_meal_from_image_base64`**.
4. Use case uses **`infrastructure/ai`** (vision) then **`infrastructure/nutrition`** (CSV) and returns **`MealAnalysisResult`** → serialized with **`to_api_dict()`** (legacy JSON shape).
5. User confirms → **`POST /meals/save`** → **`persist_meal_to_database`** → **`db/repository`**.

Telegram does **not** import core directly in this deployment; the HTTP boundary matches a split Railway setup (bot service + API service). A co-located MAX or web client can either call the same HTTP API or import use cases in-process.

## Flow: Streamlit (`ui.py`)

Streamlit calls **`POST /generate_response`** (legacy) or can use `/meals/*` — same backend as Telegram.

## Adding a new channel (e.g. MAX)

1. Add `app/interfaces/max/` with handlers analogous to Telegram: parse user input, build base64 or text, call **`/meals/analyze`** or **`/meals/analyze-text`**, then **`/meals/save`** with a stable user id field (today `telegram_id` in API bodies; rename or generalize in a later migration).
2. Keep keyboards and callback strings **inside** the MAX package, not in `core/`.
3. Reuse **`MealAnalysisResult`** / **`MealLogRequest`** if you call Python use cases in-process instead of HTTP.

## Compatibility shims

- **`app.services.openai_vision`** / **`app.services.nutrition_service`** re-export **`infrastructure`** implementations.
- **`app.api.routes_*`** re-export routers from **`app.interfaces.api`**.
- **`app.bot.*`** re-export **`app.interfaces.telegram.*`** so existing commands and imports keep working.

## Environment & deploy

Unchanged: `uvicorn service:app`, `python -m app.bot.telegram_bot`, same env vars (`OPENAI_API_KEY`, `BASE_URL`, `DATABASE_URL`, …).
