#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

choose_py(){
  for p in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$p" >/dev/null 2>&1; then
      if "$p" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3,11) else 1)
PY
      then echo "$p"; return; fi
    fi
  done
  return 1
}

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "[GGS] Creating .env from .env.example"
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export GGS_MODE=PAPER
export GGS_ROOT="$ROOT"
export GGS_PORT="${GGS_PORT:-6969}"

PYBIN="$(choose_py || true)"
if [[ -z "$PYBIN" ]]; then echo "[GGS] Python 3.11+ required"; exit 1; fi
if [[ -x .venv/bin/python ]] && ! .venv/bin/python - <<'PYV' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3,11) else 1)
PYV
then
  echo "[GGS] Existing .venv uses Python <3.11; rebuilding for LIVE SDK compatibility..."
  rm -rf .venv
fi
if [[ ! -x .venv/bin/python ]]; then
  echo "[GGS] Creating .venv with $PYBIN..."
  "$PYBIN" -m venv .venv
fi
source .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
mkdir -p runtime/paper

export SSL_CERT_FILE="$(python -m certifi)"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"

PORT="$GGS_PORT"
if command -v lsof >/dev/null 2>&1; then
  OLD="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  [[ -n "$OLD" ]] && kill $OLD 2>/dev/null || true
fi

for f in runtime/paper/engine.pid runtime/paper/dashboard.pid runtime/paper/telegram.pid; do
  if [[ -f "$f" ]]; then
    pid="$(cat "$f" 2>/dev/null || true)"
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  fi
done

nohup python -m ggs.runtime > runtime/paper/engine.log 2>&1 & echo $! > runtime/paper/engine.pid
nohup python -m uvicorn ggs.app:app --host 127.0.0.1 --port "$PORT" > runtime/paper/dashboard.log 2>&1 & echo $! > runtime/paper/dashboard.pid

if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_OWNER_ID:-}" ]]; then
  nohup python -m ggs.telegram.bot > runtime/paper/telegram.log 2>&1 & echo $! > runtime/paper/telegram.pid
  TELEGRAM_STATUS="ON"
else
  TELEGRAM_STATUS="OFF (configure .env)"
fi
sleep 1

echo
echo "GGS — Ganteng-Ganteng Signature"
echo "Runtime: PAPER / LIVE READ-ONLY / SHADOW / LIVE via Telegram /mode"
echo "Dashboard: http://127.0.0.1:$PORT"
echo "Telegram: $TELEGRAM_STATUS"
