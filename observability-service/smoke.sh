#!/usr/bin/env bash
# End-to-end monitoring check: a REAL Prometheus scrapes /actuator/metrics
# and the business metric must be queryable through its API.
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

curl -sf -X POST localhost:8000/api/v1/jobs -H 'Content-Type: application/json' -d '{"payload": "metered"}' >/dev/null
curl -sf -X POST localhost:8000/api/v1/jobs -H 'Content-Type: application/json' -d '{"payload": "metered-2"}' >/dev/null

echo "waiting for prometheus to scrape..."
for i in $(seq 1 30); do
  up=$(curl -sfG 'localhost:9090/api/v1/query' --data-urlencode 'query=up{job="observability-service"}' | grep -o '"value":\[[^]]*"1"\]' || true)
  [ -n "$up" ] && break
  sleep 2
done
[ -n "$up" ] || { echo "prometheus never scraped the app"; curl -s localhost:9090/api/v1/targets | tail -5; exit 1; }

# instant queries return the LAST scraped sample, which may predate the
# POSTs above: retry until a scrape after them lands (2s interval)
value=0
for i in $(seq 1 15); do
  result=$(curl -sfG 'localhost:9090/api/v1/query' --data-urlencode 'query=jobs_accepted_total')
  value=$(echo "$result" | grep -oE '"[0-9]+(\.[0-9]+)?"\]' | tr -d '"]' | head -1)
  [ -n "$value" ] && [ "${value%.*}" -ge 2 ] && break
  sleep 2
done
echo "query jobs_accepted_total: $result"
[ "${value%.*}" -ge 2 ] || { echo "expected at least 2 accepted jobs, got ${value:-none}"; exit 1; }

echo "SMOKE OK: prometheus scraped /actuator/metrics and jobs_accepted_total=$value is queryable"
