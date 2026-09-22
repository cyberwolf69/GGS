#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo "[GGS] Run ./start.sh once first to create .venv."; exit 1; }
if [[ -f .env ]]; then set -a; source .env; set +a; fi
source .venv/bin/activate
python -m ggs.live.check "$@"
