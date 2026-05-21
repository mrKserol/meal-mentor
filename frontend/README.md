# Meal Mentor — frontend

SPA on **React + Vite + TypeScript + Tailwind**: dashboard, nutrition diary, profile onboarding, sign-in (email/password, **Telegram**, **Yandex**), **PWA** (`manifest`, `sw.js` in `public/`).

| Docs | |
|------|--|
| Русский | [docs/README.ru.md](../docs/README.ru.md) |
| English | [docs/README.en.md](../docs/README.en.md) |
| Root | [README.md](../README.md) |

## Environment

Copy `.env` from `.env.example`:

```bash
VITE_API_URL=http://127.0.0.1:8000
# OAuth (optional for local login buttons)
VITE_TELEGRAM_CLIENT_ID=
VITE_TELEGRAM_REDIRECT_URI=http://localhost:5173/auth/telegram/callback
VITE_YANDEX_CLIENT_ID=
VITE_YANDEX_REDIRECT_URI=http://localhost:5173/auth/yandex/callback
VITE_YANDEX_SCOPES=login:info login:email login:avatar login:birthday
```

For production, set `VITE_API_URL` to your deployed FastAPI URL and matching OAuth redirect URIs.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Local development (Vite, default http://localhost:5173) |
| `npm run build` | Production build (`tsc` + Vite → `dist/`) |
| `npm run preview` | Preview production build |
| `npm run start` | Serve `dist` statically (e.g. Railway) |

## Routes (high level)

- `/login`, `/register` — auth
- `/auth/telegram/callback`, `/auth/yandex/callback` — OAuth
- `/dashboard`, `/diary`, `/onboarding/profile` — main app
- `/admin` — admin panel (`role=admin`)

Web meal AI calls use JWT endpoints under `/users/me/meals/*` (plan limits apply). See full API tables in the docs above.

## Contributors

- Shared meal-flow helpers: **`src/utils/mealFlow.ts`**
- Do **not** add a `frontend/src/lib/` tree: root `.gitignore` ignores `lib/` (Python), so those files would not be committed.
- Admin feature presets: **`src/admin/featurePresets.ts`**
