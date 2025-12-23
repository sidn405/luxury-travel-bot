# Use a slim Python base image
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
        gcc libcairo2-dev pkg-config python3-dev \
        libdbus-1-dev libgirepository1.0-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# IMPORTANT: use shell so $PORT expands; also fix the double colon; use exec
CMD ["bash","-lc","exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 8 Luxury_Travel_Bot:app"]









