FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --uid 10001 bot \
    && mkdir -p /app/data /app/.runtime \
    && chown -R bot:bot /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=bot:bot . .
USER bot

ENV MANGA_BOT_DATABASE_PATH=/app/data/manga_bot.db \
    MANGA_BOT_INSTANCE_LOCK_PATH=/app/.runtime/void_translator.lock

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -m utils.healthcheck || exit 1

CMD ["python", "main.py"]
