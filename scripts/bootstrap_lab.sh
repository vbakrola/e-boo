#!/usr/bin/env bash
# ==============================================================================
# Ubuntu Lab Manager - 10-PC Controlled Lab Bootstrap Script
# Deploys and starts the agent across all 10 Ubuntu PCs over LAN SSH.
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Ubuntu Lab Manager: 10-PC Lab Bootstrap ===${NC}"

SERVER_URL="${1:-}"
TOKEN="${2:-}"
HOSTS_FILE="${3:-lab_hosts.txt}"

if [[ -z "$SERVER_URL" || -z "$TOKEN" ]]; then
    echo "Usage: ./bootstrap_lab.sh <SERVER_URL> <ENROLLMENT_TOKEN> [HOSTS_FILE]"
    echo "Example: ./bootstrap_lab.sh https://192.168.1.50:8000 enroll_lab_abc123 lab_hosts.txt"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Create a sample hosts file if it does not exist
if [[ ! -f "$HOSTS_FILE" ]]; then
    echo -e "${YELLOW}Creating default template '${HOSTS_FILE}' with 10 PCs...${NC}"
    cat <<EOF > "$HOSTS_FILE"
# Format: IP_ADDRESS HOSTNAME SSH_USER
192.168.1.101 LAB-PC-01 labadmin
192.168.1.102 LAB-PC-02 labadmin
192.168.1.103 LAB-PC-03 labadmin
192.168.1.104 LAB-PC-04 labadmin
192.168.1.105 LAB-PC-05 labadmin
192.168.1.106 LAB-PC-06 labadmin
192.168.1.107 LAB-PC-07 labadmin
192.168.1.108 LAB-PC-08 labadmin
192.168.1.109 LAB-PC-09 labadmin
192.168.1.110 LAB-PC-10 labadmin
EOF
    echo "Please adjust IP addresses and credentials in ${HOSTS_FILE} if needed."
fi

CA_CERT_PATH="$REPO_DIR/certs/ca.crt"

echo -e "${BLUE}Reading target hosts from ${HOSTS_FILE}...${NC}"

while IFS=' ' read -r ip hostname ssh_user || [[ -n "$ip" ]]; do
    # Skip comments and blank lines
    [[ "$ip" =~ ^#.*$ || -z "$ip" ]] && continue
    ssh_user="${ssh_user:-labadmin}"

    echo -e "\n${BLUE}--- Deploying to ${hostname} (${ip}) as ${ssh_user} ---${NC}"
    
    # 1. Test ping / connectivity
    if ! ping -c 1 -W 2 "$ip" &>/dev/null; then
        echo -e "${RED}[SKIPPED] ${hostname} (${ip}) is currently unreachable on LAN. Continue with others.${NC}"
        continue
    fi

    # 2. Copy agent code and install script
    echo "Transferring agent bundle to ${ip}..."
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "${ssh_user}@${ip}" "mkdir -p /tmp/ubuntu-lab-install"
    scp -r "$REPO_DIR/agent" "$REPO_DIR/deployment" "$REPO_DIR/scripts/install_agent.sh" "${ssh_user}@${ip}:/tmp/ubuntu-lab-install/"
    
    # Copy CA cert if present
    if [[ -f "$CA_CERT_PATH" ]]; then
        scp "$CA_CERT_PATH" "${ssh_user}@${ip}:/tmp/ubuntu-lab-install/ca.crt"
        CA_FLAG="--ca-cert /tmp/ubuntu-lab-install/ca.crt"
    else
        CA_FLAG=""
    fi

    # 3. Execute installation with sudo
    echo "Running agent installer on ${hostname}..."
    ssh -t "${ssh_user}@${ip}" "sudo bash /tmp/ubuntu-lab-install/install_agent.sh --server '${SERVER_URL}' --token '${TOKEN}' --hostname '${hostname}' ${CA_FLAG}"
    
    # 4. Clean up temp folder
    ssh "${ssh_user}@${ip}" "rm -rf /tmp/ubuntu-lab-install"
    echo -e "${GREEN}[SUCCESS] Agent installed and connected on ${hostname}.${NC}"

done < "$HOSTS_FILE"

echo -e "\n${GREEN}=== Lab Bootstrap Completed! Check dashboard for device statuses. ===${NC}"
