# Meal Mentor — фронтенд

SPA на **React + Vite + TypeScript + Tailwind**: дашборд, дневник питания, онбординг профиля, вход (email/пароль, Telegram), **PWA** (манифест и `sw.js` в `public/`).

Полное описание продукта, API и запуска бэкенда — в [корневом README](../README.md).

## Окружение

Создайте `.env` из `.env.example`:

```bash
VITE_API_URL=http://127.0.0.1:8000
```

Для продакшена укажите URL развёрнутого FastAPI (например Railway).

## Скрипты

| Команда | Назначение |
|---------|------------|
| `npm run dev` | Локальная разработка (Vite) |
| `npm run build` | Сборка (`tsc` + Vite) |
| `npm run preview` | Просмотр production-сборки |
| `npm run start` | Статическая отдача `dist` (например на Railway) |

## Важно для контрибьюторов

- Общие хелперы анализа приёма пищи лежат в **`src/utils/mealFlow.ts`**. Каталог с именем `lib/` в путях фронта **не используется**: в корневом `.gitignore` есть правило `lib/` (для Python), из‑за него файлы в `frontend/src/lib/` не попадали бы в git.
