#!/bin/sh
set -e

echo "🚀 Migratsiyalar bajarilmoqda..."
python manage.py migrate --noinput

echo "🌍 Lokalizatsiya fayllarini compile qilinmoqda..."
python manage.py compilemessages || echo "No translation files found"

echo "📦 Static fayllar yig'ilmoqda..."
python manage.py collectstatic --noinput

echo "✅ Django tayyor. Gunicorn ishga tushirilmoqda..."
exec gunicorn --workers=3 --timeout=120 --bind 0.0.0.0:8000 config.wsgi:application
