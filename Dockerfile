FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

# Railway will use this for the API service.
# For the bot service, override Start Command to: python -m app.bot.telegram_bot
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]

