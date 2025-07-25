FROM python:3.10-slim

WORKDIR /app

# Sistem paketlarini o'rnatish
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# pip ni yangilash
RUN pip install --upgrade pip

# Python paketlarini o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni nusxalash
COPY . .

RUN useradd -m myuser
USER myuser

# Portlarni ochish (web uchun)
EXPOSE 8000

# Django serveri uchun default komanda (bot uchun alohida xizmat belgilaymiz)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]