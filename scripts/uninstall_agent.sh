#!/usr/bin/env bash
# ==============================================================================
# Ubuntu Lab Manager - Agent Uninstallation Script
# Removes systemd service and local agent files cleanly from target Ubuntu PC.
# ==============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
   echo "Error: This script must be run as root (or via sudo)." 1>&2
   exit 1
fi

echo "Stopping and disabling ubuntu-lab-agent systemd service..."
systemctl stop ubuntu-lab-agent.service || true
systemctl disable ubuntu-lab-agent.service || true

rm -f /etc/systemd/system/ubuntu-lab-agent.service
systemctl daemon-reload

echo "Removing agent application and configuration files..."
rm -rf /opt/ubuntu-lab-manager
rm -rf /etc/ubuntu-lab-manager

echo "Ubuntu Lab Agent uninstalled successfully."
