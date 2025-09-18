FROM python:3.11-slim-bullseye
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 appuser && \
    mkdir -p staticfiles && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
