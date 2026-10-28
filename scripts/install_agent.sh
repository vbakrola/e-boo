#!/usr/bin/env bash
# ==============================================================================
# Ubuntu Lab Manager - Agent Installation Script for Ubuntu 20.04/22.04/24.04
# Run as root or with sudo on target Ubuntu PC.
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Ubuntu Lab Manager - PC Agent Installer ===${NC}"

if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (or via sudo).${NC}" 1>&2
   exit 1
fi

SERVER_URL=""
TOKEN=""
HOSTNAME_OVERRIDE=""
CA_CERT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --server)
      SERVER_URL="$2"
      shift 2
      ;;
    --token|--enrollment-token)
      TOKEN="$2"
      shift 2
      ;;
    --hostname)
      HOSTNAME_OVERRIDE="$2"
      shift 2
      ;;
    --ca-cert)
      CA_CERT="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: sudo bash install_agent.sh --server <URL> --token <TOKEN> [--hostname <HOSTNAME>] [--ca-cert <PATH>]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$SERVER_URL" || -z "$TOKEN" ]]; then
  echo -e "${RED}Error: --server and --token are required arguments.${NC}"
  echo "Example: sudo bash install_agent.sh --server https://192.168.1.50:8000 --token enroll_lab_xyz --hostname LAB-PC-01"
  exit 1
fi

echo -e "${BLUE}1. Checking Python 3 environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Installing python3..."
    apt-get update -y && apt-get install -y python3
fi
echo "Python 3 is ready: $(python3 --version)"

echo -e "${BLUE}2. Installing Root CA certificate if provided...${NC}"
if [[ -n "$CA_CERT" && -f "$CA_CERT" ]]; then
    cp "$CA_CERT" /usr/local/share/ca-certificates/ubuntu-lab-ca.crt
    update-ca-certificates
    echo "CA certificate installed and trusted."
fi

echo -e "${BLUE}3. Setting up agent files in /opt/ubuntu-lab-manager...${NC}"
mkdir -p /opt/ubuntu-lab-manager/agent
mkdir -p /etc/ubuntu-lab-manager
chmod 700 /etc/ubuntu-lab-manager

# Copy files from repository directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cp -r "$REPO_DIR/agent/"* /opt/ubuntu-lab-manager/agent/
chmod +x /opt/ubuntu-lab-manager/agent/agent.py

echo -e "${BLUE}4. Enrolling PC with central server...${NC}"
CMD=(python3 /opt/ubuntu-lab-manager/agent/agent.py register --server "$SERVER_URL" --enrollment-token "$TOKEN" --config /etc/ubuntu-lab-manager/agent.conf)
if [[ -n "$HOSTNAME_OVERRIDE" ]]; then
    CMD+=(--hostname "$HOSTNAME_OVERRIDE")
fi

"${CMD[@]}"

echo -e "${BLUE}5. Installing and starting systemd service...${NC}"
cp "$REPO_DIR/deployment/systemd/ubuntu-lab-agent.service" /etc/systemd/system/ubuntu-lab-agent.service
systemctl daemon-reload
systemctl enable ubuntu-lab-agent.service
systemctl restart ubuntu-lab-agent.service

echo -e "${GREEN}=== Ubuntu Lab Agent Successfully Installed and Started! ===${NC}"
systemctl status ubuntu-lab-agent.service --no-pager
