#!/usr/bin/env bash
# End-to-end smoke over docker compose: build, boot, exercise, tear down.
set -euo pipefail
cd "$(dirname "$0")"

cleanup() { docker compose down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker compose up -d --build

echo "waiting for the app healthcheck..."
for i in $(seq 1 30); do
  state=$(docker compose ps --format '{{.Health}}' app 2>/dev/null || echo starting)
  [ "$state" = "healthy" ] && break
  sleep 2
done
[ "$state" = "healthy" ] || { echo "app never became healthy"; docker compose logs app | tail -20; exit 1; }

body=$(curl -sf -X POST localhost:8000/api/v1/orders -H 'Content-Type: application/json' -d '{"sku": "LATTE", "quantity": 2}')
echo "placed: $body"
echo "$body" | grep -q '"amount_cents":780'

curl -sf localhost:8000/api/v1/orders | grep -q LATTE
curl -sf localhost:8000/actuator/health | grep -q UP
curl -sf localhost:8000/actuator/info | grep -q compose

echo "SMOKE OK: order placed against postgres, cache on redis, health UP"
