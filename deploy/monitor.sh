#!/bin/bash
cd /opt/placd

echo "=== $(date) ==="
echo ""

echo "--- Services ---"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "--- Resources ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo ""
echo "--- Job Counts ---"
docker compose exec -T postgres psql -U placd -c "
SELECT
    source_platform,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status='active') as active,
    COUNT(*) FILTER (WHERE trust_score >= 100) as faang,
    MAX(created_at)::date as latest
FROM jobs
GROUP BY source_platform
ORDER BY total DESC;
" 2>/dev/null || echo "DB not ready"

echo ""
echo "--- Top FAANG Jobs Today ---"
docker compose exec -T postgres psql -U placd -c "
SELECT company, COUNT(*) as jobs
FROM jobs
WHERE trust_score = 100
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY company
ORDER BY jobs DESC
LIMIT 10;
" 2>/dev/null

echo ""
echo "--- Queue Depths ---"
for queue in crawl_tier_a crawl_tier_b crawl_tier_c enrich; do
    depth=$(docker compose exec -T redis redis-cli llen celery:$queue 2>/dev/null || echo "?")
    echo "  $queue: $depth"
done

echo ""
echo "--- Spam Filtered (24h) ---"
docker compose exec -T postgres psql -U placd -c "
SELECT COUNT(*) as spam_rejected
FROM jobs
WHERE is_spam = true
  AND created_at > NOW() - INTERVAL '24 hours';
" 2>/dev/null
