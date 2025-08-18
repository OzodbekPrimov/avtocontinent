# 1. Builder bosqichi
FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    gettext \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 2. Runtime bosqichi
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    gettext \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
   CMD curl -f http://localhost:8000/ || exit 1

CMD ["gunicorn", "--workers=3", "--timeout=120", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "config.wsgi:application"]
