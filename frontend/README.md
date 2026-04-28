# Meal Mentor Frontend

Placeholder directory for the upcoming web UI.

## Planned stack

- React/Next.js or Vite SPA
- Auth flow with `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`
- Profile screen backed by `GET /users/me`

## Notes

- Keep access token in memory (short-lived).
- Store refresh token securely and rotate via `/auth/refresh`.
