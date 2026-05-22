# Meal Mentor

**Meal Mentor** — сервис учёта питания: веб-приложение (дашборд, дневник, профиль), Telegram-бот и API на **FastAPI**. Расчёт **КБЖУ** по локальной базе продуктов (`nutrition.csv`), распознавание блюд по фото и тексту через **OpenAI**, тарифы и лимиты использования AI-функций.

| Документация | |
|--------------|--|
| **Русский** | [docs/README.ru.md](docs/README.ru.md) |
| **English** | [docs/README.en.md](docs/README.en.md) |
| Архитектура слоёв | [docs/architecture.md](docs/architecture.md) |
| Фронтенд (кратко) | [frontend/README.md](frontend/README.md) |

---

## Быстрый старт

**Backend**

```bash
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY, JWT_SECRET_KEY, DATABASE_URL, …
alembic upgrade head
uvicorn service:app --reload
```

**Frontend**

```bash
cd frontend
cp .env.example .env   # VITE_API_URL, OAuth (Telegram / Yandex)
npm install
npm run dev
```

**Telegram-бот** (отдельный процесс, нужен `BASE_URL` на API):

```bash
python -m app.bot.telegram_bot
```

---

## Quick start

**Backend**

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn service:app --reload
```

**Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

**Telegram bot**

```bash
python -m app.bot.telegram_bot
```

---

## Стек

| Слой | Технологии |
|------|------------|
| API | FastAPI, SQLAlchemy, Alembic, JWT |
| AI | OpenAI (vision + text) |
| Nutrition | `data/nutrition.csv`, aliases, fuzzy / optional semantic match; soup category scoring (see docs) |
| Web UI | React, Vite, TypeScript, Tailwind, PWA |
| Bot | Python, long polling → HTTP API |

Полное описание возможностей, API, env, админки, OAuth, лимитов и тестов — в [docs/README.ru.md](docs/README.ru.md) и [docs/README.en.md](docs/README.en.md).
