# Possible next steps (not implemented)

Use this as a backlog after the core/interfaces split.

1. **MAX adapter** — Implement `app/interfaces/max/` with HTTP client to the same `/meals` and `/reports` endpoints (or in-process use cases if single deploy).

2. **Web frontend** — Replace or complement Streamlit with a SPA; keep using FastAPI as BFF; optional JWT/mobile-friendly auth.

3. **Mobile API preparation** — Generalize `telegram_id` in request bodies to `external_user_id` + `channel` enum; versioned API (`/v1/...`); pagination for reports.

4. **Text fallback via LLM** — Richer clarification dialog (still behind a use case, not in Telegram handlers only).

5. **Synonym / fuzzy matching layer** — Centralize ingredient normalization before CSV lookup; configurable dictionaries per locale.

6. **Migration from CSV to nutrition database** — Implement `NutritionProvider` protocol; swap `csv_nutrition_provider` for Postgres/API without changing use cases.

7. **Shared FSM store** — Redis (or similar) for `USER_STATES` when running multiple bot replicas.

8. **Structured logging / tracing** — `infrastructure/logging` with request ids across API and bots.

9. **Tests** — Contract tests for `MealAnalysisResult.to_api_dict()` and use cases with mocked OpenAI + CSV.
