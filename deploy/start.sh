#!/bin/bash
set -e
cd /opt/placd

echo "=== Building images ==="
docker compose build --no-cache

echo "=== Starting infrastructure ==="
docker compose up -d postgres redis typesense
echo "Waiting for databases (30s)..."
sleep 30

echo "=== Running migrations ==="
docker compose run --rm api alembic upgrade head

echo "=== Starting all services ==="
docker compose up -d

echo "=== Waiting for API ==="
for i in {1..30}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API healthy"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 5
done

echo "=== Running first discovery ==="
docker compose exec -T api python scripts/run_discovery_now.py

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP")
echo ""
echo "========================================="
echo "✅ Placd is live!"
echo "   Frontend : http://$PUBLIC_IP"
echo "   API Docs : http://$PUBLIC_IP:8000/docs"
echo "   Logs     : docker compose logs -f celery-worker"
echo "========================================="
