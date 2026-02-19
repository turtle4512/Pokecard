FROM python:3.12-slim

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn \
    && playwright install chromium

COPY . .

ENV PORT=5000
EXPOSE 5000

CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120 "web:create_app()"
