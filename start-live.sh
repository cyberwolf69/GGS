#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ ! -f .env && -f .env.example ]]; then cp .env.example .env; fi
set -a
# shellcheck disable=SC1091
source .env
set +a
if [[ "${GGS_LIVE_ENABLED:-false}" != "true" ]]; then
  echo "[GGS] LIVE REAL remains locked (GGS_LIVE_ENABLED=false)."
  echo "[GGS] Run ./setup-live.sh, validate READ ONLY, then SHADOW before enabling real orders."
  exit 1
fi
python3 - <<'PY2'
from ggs.state import update_settings
update_settings({"mode":"LIVE"})
print("[GGS] Persistent mode set to LIVE")
PY2
exec ./start-paper.sh
