#!/bin/sh
set -eu

HOST="${FALKORDB_HOST:-falkordb}"
PORT="${FALKORDB_PORT:-6379}"

echo "Waiting for FalkorDB at ${HOST}:${PORT}..."

python - "$HOST" "$PORT" <<'PY'
import socket
import sys
import time

host, port = sys.argv[1], int(sys.argv[2])
deadline = time.monotonic() + 180

while time.monotonic() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print("FalkorDB TCP connection is ready.")
            break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit("ERROR: FalkorDB did not become ready within 180 seconds.")
PY

exec "$@"
