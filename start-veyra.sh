#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"

echo "Building VEYRA..."
docker compose build

echo "Starting FalkorDB..."
docker compose up -d falkordb

echo "Waiting for FalkorDB..."
ready=0
for i in $(seq 1 40); do
  if docker compose exec -T falkordb redis-cli PING 2>/dev/null | grep -q PONG; then
    ready=1
    break
  fi
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  docker compose logs --tail=80 falkordb
  echo "ERROR: FalkorDB did not become ready."
  exit 1
fi

echo "Checking whether VEYRA needs initial seeding..."
docker compose run --rm --no-deps backend python -c '
from falkordb import FalkorDB
db = FalkorDB(host="falkordb", port=6379,
              socket_connect_timeout=3, socket_timeout=10)
g = db.select_graph("VEYRA")
try:
    result = g.query("MATCH (n) RETURN count(n)")
    count = int(result.result_set[0][0])
except Exception:
    count = 0
print("Existing VEYRA nodes:", count)
raise SystemExit(0 if count > 0 else 10)
' && seeded=1 || rc=$?

if [ "${seeded:-0}" != "1" ]; then
  if [ "${rc:-0}" -ne 10 ]; then
    echo "ERROR: Could not check the graph. Stopping to avoid unsafe seeding."
    exit 1
  fi

  echo "Seeding original scenarios..."
  docker compose run --rm --no-deps backend python /app/seed_graph.py

  echo "Seeding demo population..."
  docker compose run --rm --no-deps backend python /app/seed_demo_population.py
else
  echo "Graph already contains data; skipping initial seed."
fi

echo "Starting backend and frontend..."
docker compose up -d backend frontend

echo
docker compose ps
echo
echo "Open port 5173 in the Codespaces Ports tab."
echo "Backend logs: docker compose logs -f backend"
