#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
PID_DIR="${PID_DIR:-$ROOT_DIR/.run}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"
SKIP_MIGRATION="${SKIP_MIGRATION:-0}"
SKIP_MOCK_DATA="${SKIP_MOCK_DATA:-0}"

mkdir -p "$LOG_DIR" "$PID_DIR"

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "[aquant] Created .env from .env.example. Please verify database settings."
fi

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(sed 's/\r$//' "$ROOT_DIR/.env")
  set +a
fi

PUBLIC_HOST="${AQUANT_PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
PUBLIC_HOST="${PUBLIC_HOST:-127.0.0.1}"

if [[ -z "${VITE_API_BASE_URL:-}" || "${VITE_API_BASE_URL}" == *"127.0.0.1"* || "${VITE_API_BASE_URL}" == *"localhost"* ]]; then
  export VITE_API_BASE_URL="http://${PUBLIC_HOST}:${BACKEND_PORT}/api"
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "[aquant] python3 is required." >&2
    exit 1
  fi
fi

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT_DIR/.venv/bin/activate"

if [[ "$SKIP_INSTALL" != "1" ]]; then
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  if [[ -d "$ROOT_DIR/frontend" ]]; then
    (cd "$ROOT_DIR/frontend" && npm install)
  fi
fi

if [[ "$SKIP_MIGRATION" != "1" ]]; then
  python -m alembic upgrade head
fi

python - <<'PY'
from app.core.database import SystemSessionLocal
from app.services.prd_v1 import SeedService

db = SystemSessionLocal()
try:
    print("[aquant] seed:", SeedService(db).init_defaults())
finally:
    db.close()
PY

if [[ "$SKIP_MOCK_DATA" != "1" ]]; then
  python - <<'PY'
from app.core.database import SystemSessionLocal
from app.services.mock_data import MockDataService

db = SystemSessionLocal()
try:
    print("[aquant] mock:", MockDataService(db).init_all())
finally:
    db.close()
PY
fi

stop_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      echo "[aquant] stopping old process $pid from $pid_file"
      kill "$pid" >/dev/null 2>&1 || true
      sleep 1
    fi
    rm -f "$pid_file"
  fi
}

stop_pid_file "$PID_DIR/backend.pid"
stop_pid_file "$PID_DIR/frontend.pid"

nohup python -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
  >"$LOG_DIR/backend.log" 2>&1 &
echo $! > "$PID_DIR/backend.pid"

(cd "$ROOT_DIR/frontend" && nohup npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
  >"$LOG_DIR/frontend.log" 2>&1 & echo $! > "$PID_DIR/frontend.pid")

echo
echo "[aquant] started"
echo "  Backend API:  http://${PUBLIC_HOST}:${BACKEND_PORT}/api"
echo "  H5 frontend:  http://${PUBLIC_HOST}:${FRONTEND_PORT}/market"
echo "  Admin web:    http://${PUBLIC_HOST}:${FRONTEND_PORT}/admin"
echo
echo "[aquant] logs"
echo "  Backend:      $LOG_DIR/backend.log"
echo "  Frontend:     $LOG_DIR/frontend.log"
echo
echo "[aquant] pids"
echo "  Backend:      $(cat "$PID_DIR/backend.pid")"
echo "  Frontend:     $(cat "$PID_DIR/frontend.pid")"
echo
echo "To stop:"
echo "  kill \$(cat \"$PID_DIR/backend.pid\") \$(cat \"$PID_DIR/frontend.pid\")"
