FASTAPI_APP = service

.PHONY: backend bot frontend-dev run-api

backend:
	uvicorn $(FASTAPI_APP):app --reload

bot:
	python -m app.bot.telegram_bot

frontend-dev:
	cd frontend && npm run dev

run-api: backend
