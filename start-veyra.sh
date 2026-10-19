#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

NETWORK="veyra-demo_default"
DB_CONTAINER="veyra-falkordb"
DB_VOLUME="veyra-data"
DB_IMAGE="falkordb/falkordb:latest"

COMPOSE=(docker compose -f compose.yaml)

echo "===== VEYRA STARTUP ====="

echo "[1/5] Validating Compose configuration..."
"${COMPOSE[@]}" config --quiet

echo "[2/5] Ensuring the application network exists..."
if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
  docker network create "$NETWORK" >/dev/null
fi

echo "[3/5] Checking FalkorDB..."

if ! docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
  echo "No existing FalkorDB container was found."
  echo "Creating a new database with persistent storage..."

  docker volume create "$DB_VOLUME" >/dev/null

  docker run -d \
    --name "$DB_CONTAINER" \
    --restart unless-stopped \
    --network "$NETWORK" \
    --network-alias falkordb \
    -p 6379:6379 \
    -p 3000:3000 \
    -v "$DB_VOLUME:/var/lib/falkordb/data" \
    "$DB_IMAGE" >/dev/null
else
  echo "Reusing existing FalkorDB container."

  if ! docker inspect -f '{{.State.Running}}' "$DB_CONTAINER" |
       grep -qx true; then
    docker start "$DB_CONTAINER" >/dev/null
  fi

  # Attach to the application network only if not already connected.
  if ! docker network inspect "$NETWORK" \
       --format '{{range .Containers}}{{.Name}}{{"\n"}}{{end}}' |
       grep -Fxq "$DB_CONTAINER"; then
    docker network connect --alias falkordb \
      "$NETWORK" "$DB_CONTAINER"
  fi
fi

echo "Waiting for FalkorDB..."
ready=0
for _ in $(seq 1 45); do
  if docker exec "$DB_CONTAINER" redis-cli PING 2>/dev/null |
       grep -qx PONG; then
    ready=1
    break
  fi
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  echo "ERROR: FalkorDB did not become ready."
  docker logs --tail=60 "$DB_CONTAINER"
  exit 1
fi

echo "[4/5] Building and starting the application..."
"${COMPOSE[@]}" up -d --build backend frontend

echo "[5/5] Checking backend health..."
ready=0
for _ in $(seq 1 30); do
  if curl -fsS --retry 2 --retry-delay 1 --max-time 5 \
      http://localhost:8000/api/health >/dev/null 2>&1; then
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

# VEYRA_AUTO_SEED
echo "[6/6] Seeding Veyra graph data..."
docker exec veyra-demo-backend-1 python /app/backend/seed_graph.py
docker exec veyra-demo-backend-1 python /app/backend/seed_demo_population.py
echo "Veyra graph seeding completed."

echo
echo "===== VEYRA STATUS ====="
"${COMPOSE[@]}" ps

echo
echo "Frontend:      http://localhost:8080"
echo "Backend:       http://localhost:8000/api/health"
echo "Graph API:     http://localhost:8080/api/graph"
echo
echo "Graph seeding runs automatically at startup; existing graph data is preserved."
