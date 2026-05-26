FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
# sentence_transformers / torch are optional (NUTRITION_ENABLE_SEMANTIC=false by default)
# and are NOT installed here — they bloat the image by ~1 GB and cause flaky network
# failures on Railway builders. Install them manually if semantic search is needed.
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

# Railway will use this for the API service.
# For the bot service, override Start Command to: python -m app.bot.telegram_bot
CMD ["sh", "-c", "uvicorn service:app --host 0.0.0.0 --port ${PORT:-8000}"]
