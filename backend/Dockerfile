FROM python:3.11-slim

# Create a non-root user
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app
USER appuser

# Healthcheck targeting the FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

# Default command (can be overridden by docker-compose for celery)
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
