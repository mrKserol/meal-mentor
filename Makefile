STREAMLIT_APP = ui.py
FASTAPI_APP = service

.PHONY: frontend backend bot run_app

frontend:
	streamlit run $(STREAMLIT_APP)

backend:
	uvicorn $(FASTAPI_APP):app --reload &

bot:
	python -m app.bot.telegram_bot

run_app: backend frontend