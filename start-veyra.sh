#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

COMPOSE=(docker compose -f compose.yaml)

echo "===== VEYRA STARTUP ====="

echo "Validating Compose configuration..."
"${COMPOSE[@]}" config --quiet

echo "Checking existing FalkorDB container..."
if ! docker inspect veyra-falkordb >/dev/null 2>&1; then
  echo "ERROR: Existing container 'veyra-falkordb' was not found."
  echo "Start or restore the intended database manually; refusing to create a new one."
  exit 1
fi

if ! docker inspect -f '{{.State.Running}}' veyra-falkordb | grep -qx true; then
  echo "ERROR: Existing FalkorDB container is not running."
  echo "Refusing to create a replacement database automatically."
  exit 1
fi

echo "Checking database connectivity..."
if ! docker exec veyra-falkordb redis-cli PING | grep -q PONG; then
  echo "ERROR: FalkorDB did not respond to PING."
  exit 1
fi

echo "Starting backend and frontend using compose.yaml..."
"${COMPOSE[@]}" up -d --build backend frontend

echo "Waiting for backend health..."
ready=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 3 http://localhost:8000/api/health >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  echo "ERROR: Backend health check failed."
  "${COMPOSE[@]}" logs --tail=80 backend
  exit 1
fi

echo
echo "===== VEYRA STATUS ====="
"${COMPOSE[@]}" ps

echo
echo "Frontend: http://localhost:8080"
echo "Backend health: http://localhost:8000/api/health"
echo "Graph API: http://localhost:8080/api/graph"
echo
echo "No database creation, reset, or seeding was performed."
