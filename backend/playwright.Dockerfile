FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Create a non-root user
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Ensure playwright stealth is installed if not in requirements
RUN pip install --default-timeout=100 --no-cache-dir playwright-stealth

# Copy source
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

# Force playwright enabled
ENV PLAYWRIGHT_ENABLED=true

# Entrypoint for celery
CMD ["celery", "-A", "workers.crawlers", "worker", "--concurrency=3", "--queues=playwright"]
