#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SRC="$ROOT/deploy/ggs.service"
SERVICE_DST="/etc/systemd/system/ggs.service"
USER_NAME="${SUDO_USER:-$USER}"

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo ./deploy/install-systemd.sh" >&2
  exit 1
fi

# Patch template to current path/user during installation.
sed \
  -e "s|User=YOUR_VPS_USER|User=$USER_NAME|" \
  -e "s|WorkingDirectory=/opt/GGS|WorkingDirectory=$ROOT|" \
  -e "s|Environment=GGS_ROOT=/opt/GGS|Environment=GGS_ROOT=$ROOT|" \
  -e "s|ExecStart=/opt/GGS/deploy/run-vps.sh|ExecStart=$ROOT/deploy/run-vps.sh|" \
  -e "s|ReadWritePaths=/opt/GGS/runtime|ReadWritePaths=$ROOT/runtime|" \
  "$SERVICE_SRC" > "$SERVICE_DST"

systemctl daemon-reload
systemctl enable ggs.service
echo "Installed $SERVICE_DST"
echo "Start with: sudo systemctl start ggs"
echo "Logs: journalctl -u ggs -f"
