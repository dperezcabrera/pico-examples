#!/usr/bin/env bash
# End-to-end over docker compose: a real broker, publisher and consumers in one container.
set -euo pipefail
cd "$(dirname "$0")"

cleanup() { docker compose down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker compose build -q app
docker compose run --rm app
