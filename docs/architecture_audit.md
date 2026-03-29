# Architecture audit — Meal Mentor

**Status:** the minimal reorganization described in §6 below is **implemented** in the repo. This document still documents the pre-change mental model and the mapping to the target layout.

---

## Pre-refactor snapshot (reference)

## 1. Entry points

| Entry | Role |
|--------|------|
| `service.py` / `uvicorn service:app` | FastAPI app (`app.main`) |
| `python -m app.bot.telegram_bot` | Telegram long-polling bot |
| `streamlit run ui.py` | Demo web UI (HTTP client to API) |
| `alembic upgrade head` | DB migrations |

## 2. Current layout (before this refactor)

| Area | Location | Notes |
|------|-----------|--------|
| **HTTP API** | `app/api/routes_*.py` | Users, meals, reports; depends on `meal_service`, `repository`, `report_service` |
| **Telegram** | `app/bot/` | Handlers, FSM in `USER_STATES`, HTTP calls to `BASE_URL` (same API) |
| **Business flow** | `app/services/meal_service.py` | Analyze photo/text, attach CSV nutrition, persist meals |
| **OpenAI** | `app/services/openai_vision.py` | Vision + text JSON parsing (`ingredients`, `confidence`) |
| **nutrition.csv** | `app/services/nutrition_service.py` | Pandas + fuzzy (+ optional semantic) |
| **DB** | `app/db/models.py`, `session.py`, `repository.py` | SQLAlchemy, PostgreSQL/SQLite |
| **Reports** | `app/services/report_service.py` | Aggregates `MealItemNutrition` |
| **Recommendations** | `app/services/recommendation_service.py` | Stub |
| **Config / prompts** | `app/core/config.py`, `app/core/prompts.py` | Env, paths to `data/promt*.txt` |

## 3. Dependency graph (simplified)

```
ui.py / Telegram handlers
    → HTTP → FastAPI routes
        → meal_service
            → openai_vision + nutrition_service + repository

report_service → repository + models
routes_reports → report_service
```

Telegram **does not** import `meal_service` directly; it only talks to the API over HTTP (suitable for split Railway services).

## 4. Telegram-specific vs universal

**Telegram-specific (must stay out of “core nutrition AI”):**

- `handlers_*`, `telegram_bot.py`, `meal_messages.py` (keyboards, Russian copy)
- `states.py` (`USER_STATES`)
- Downloading `Photo` → bytes / base64
- `callback_data` `meal_yes` / `meal_no`

**Already universal (candidates for “core”):**

- JSON normalization + OpenAI calls (`openai_vision`)
- CSV matching + macro totals (`nutrition_service`)
- Meal persistence (`repository` + `create_meal`)
- Report aggregation (`report_service`)

**Mixed (orchestration):**

- `meal_service` — chains vision → nutrition → optional DB; **no** Telegram types.

## 5. What already matched the target vision

- API and Telegram are **separate processes** with HTTP boundary (good for MAX/web/mobile).
- `meal_service` is **not** importing `telegram.*`.
- Nutrition and vision are **separate classes** (only file placement was under `services/`).

## 6. Gaps vs target (were present before refactor; now addressed)

- **Use case entry** → `app/core/use_cases/meal_analysis.py` (`analyze_meal_from_image_base64`, etc.).
- **Shared models** → `app/core/schemas.py` (`MealAnalysisResult`, `MealLogRequest`, …) + `to_api_dict()` for legacy JSON.
- **OpenAI / CSV** → `app/infrastructure/ai/`, `app/infrastructure/nutrition/` with **shims** under `app/services/`.
- **Interfaces namespace** → `app/interfaces/api/`, `app/interfaces/telegram/` with **shims** under `app/api/`, `app/bot/`.

---

## Minimal refactor plan (executed)

1. **Add** `app/infrastructure/ai/openai_food_client.py` and `app/infrastructure/nutrition/csv_nutrition_provider.py` (move implementation); keep `app/services/openai_vision.py` and `nutrition_service.py` as **thin re-exports** (no import breakage).
2. **Add** `app/core/schemas.py` (`MealAnalysisResult`, `MealLogRequest`, `MealLogResponse`, `MacroTotals`, `DetectedIngredient`).
3. **Add** `app/core/use_cases/meal_analysis.py` — `analyze_meal_from_image_base64`, `analyze_meal_from_text`, `persist_meal_to_database`, `analyze_and_log_meal_legacy`; **same behavior** as current `meal_service`.
4. **Point** FastAPI routes and `main.py` `/generate_response` at use cases (or thin `meal_service` wrappers).
5. **Move** `app/api/*` → `app/interfaces/api/*`; **shim** old `app/api/routes_*.py` to re-export `router`.
6. **Move** `app/bot/*` → `app/interfaces/telegram/*`; **shim** `app/bot/*.py` for `python -m app.bot.telegram_bot` and stable imports.
7. **Add** stubs: `interfaces/max/`, `interfaces/web/` (docs only / pointer to `ui.py`).
8. **Leave** `app/db/*` and `app/core/config.py` in place (Alembic + env stability); document as future `infrastructure/db` move.
9. **Docs**: `docs/architecture.md`, `docs/refactor_next_steps.md`; update `README.md`.

### Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Broken imports | Shims at old `app.api` / `app.bot` / `app.services` paths |
| Railway CMD | Still `uvicorn service:app` and `python -m app.bot.telegram_bot` |
| Alembic | Still imports `app.db.models` and `app.core.config` — unchanged |

### Reversibility

Remove `interfaces/*` shims and restore single copy under `app/api` and `app/bot` if needed; infrastructure files can be inlined back into `services/`.
