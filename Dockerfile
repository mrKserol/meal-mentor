FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
# Slow / flaky CI: bump timeouts; sentence_transformers pulls torch — CPU wheel avoids multi‑GB NVIDIA/CUDA stacks from PyPI.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --retries 10 torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --retries 10 -r /app/requirements.txt

COPY . /app

EXPOSE 8000

# Railway will use this for the API service.
# For the bot service, override Start Command to: python -m app.bot.telegram_bot
CMD ["sh", "-c", "uvicorn service:app --host 0.0.0.0 --port ${PORT:-8000}"]
