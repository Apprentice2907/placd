#!/bin/bash
cd /opt/placd
if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "$(date): API down — restarting"
    docker compose up -d
fi
