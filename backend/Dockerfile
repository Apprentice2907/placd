FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl wget git gcc g++ \
    libnss3 libatk-bridge2.0-0 libdrm2 \
    libxkbcommon0 libgbm1 libasound2 \
    libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN useradd -m placd && chown -R placd:placd /app
USER placd

EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
