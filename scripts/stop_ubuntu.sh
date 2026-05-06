#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${PID_DIR:-$ROOT_DIR/.run}"

stop_one() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  if [[ ! -f "$pid_file" ]]; then
    echo "[aquant] ${name}: no pid file"
    return
  fi
  local pid
  pid="$(cat "$pid_file" || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    echo "[aquant] stopping ${name} pid=${pid}"
    kill "$pid" >/dev/null 2>&1 || true
  else
    echo "[aquant] ${name}: process not running"
  fi
  rm -f "$pid_file"
}

stop_one backend
stop_one frontend
