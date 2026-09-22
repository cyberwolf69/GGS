#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
for name in engine dashboard telegram; do
  f="runtime/paper/$name.pid"
  if [[ -f "$f" ]]; then
    pid="$(cat "$f" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "$name: RUNNING (pid $pid)"
    else
      echo "$name: STOPPED"
    fi
  else
    echo "$name: NOT STARTED"
  fi
done
