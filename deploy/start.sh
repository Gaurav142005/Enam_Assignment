#!/bin/sh
# Boots the API and the web app in one container. If either exits, the container exits and the platform restarts it.
set -e

mkdir -p "$FINN_CACHE_DIR"
# FINN_RESEED=1 replaces the database with the bundled snapshot on boot (e.g. after shipping a fresher one). Opt-in:
# it discards anything changed on the live deployment since.
if [ "${FINN_RESEED:-0}" = "1" ] && [ -f /app/api/seed/finn.db.gz ]; then
  echo "FINN_RESEED=1: replacing the database with the bundled snapshot"
  rm -f "$FINN_CACHE_DIR/finn.db" "$FINN_CACHE_DIR/finn.db-wal" "$FINN_CACHE_DIR/finn.db-shm"
fi
if [ ! -f "$FINN_CACHE_DIR/finn.db" ] && [ -f /app/api/seed/finn.db.gz ]; then
  echo "Seeding $FINN_CACHE_DIR/finn.db from the bundled snapshot"
  gunzip -c /app/api/seed/finn.db.gz > "$FINN_CACHE_DIR/finn.db"
fi

cd /app/api
/app/api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 &
API_PID=$!

cd /app/web
HOSTNAME=0.0.0.0 node server.js &
WEB_PID=$!

# Exit as soon as either process dies.
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do sleep 5; done
echo "A process exited; stopping the container"
kill "$API_PID" "$WEB_PID" 2>/dev/null || true
exit 1
