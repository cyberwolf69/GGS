#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
for mode in paper live; do
  for name in telegram dashboard engine; do
    f="runtime/$mode/$name.pid"
    if [[ -f "$f" ]]; then
      pid="$(cat "$f" 2>/dev/null || true)"
      if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then kill "$pid" 2>/dev/null || true; fi
      rm -f "$f"
    fi
  done
done
echo "GGS stopped."
