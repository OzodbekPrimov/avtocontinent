# 1. Builder bosqichi: dependencies o'rnatish
FROM python:3.10-slim AS builder

WORKDIR /app

# Tizim kutubxonalarini o'rnatamiz
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# PIPni yangilash va dependencies o'rnatish (user katalogida)
COPY requirements.txt .
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# 2. Yakuniy image (runtime uchun)
FROM python:3.10-slim

# Non-root user yaratamiz (security uchun)
RUN useradd -m -u 1000 appuser

# Runtime uchun kerakli kutubxonalar
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Builderdan pip o'rnatilgan paketlarni nusxalash
COPY --from=builder /root/.local /home/appuser/.local

# Ilova kodini qo'shish
COPY --chown=appuser:appuser . .

# PATH va python parametrlarini sozlash
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

# Production uchun Gunicorn serverini ishga tushiramiz
CMD ["gunicorn", "--workers=3", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
