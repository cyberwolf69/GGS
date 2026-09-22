#!/usr/bin/env bash
set -euo pipefail
ROOT="${GGS_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export GGS_MODE="${GGS_MODE:-PAPER}"
export GGS_PORT="${GGS_PORT:-6969}"
export SSL_CERT_FILE="$(.venv/bin/python -m certifi)"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
mkdir -p runtime/paper

pids=()
cleanup(){
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

.venv/bin/python -m ggs.runtime >> runtime/paper/engine.log 2>&1 & pids+=("$!")
.venv/bin/python -m uvicorn ggs.app:app --host "${GGS_HOST:-127.0.0.1}" --port "$GGS_PORT" >> runtime/paper/dashboard.log 2>&1 & pids+=("$!")

if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_OWNER_ID:-}" ]]; then
  .venv/bin/python -m ggs.telegram.bot >> runtime/paper/telegram.log 2>&1 & pids+=("$!")
fi

wait -n "${pids[@]}"
exit 1
