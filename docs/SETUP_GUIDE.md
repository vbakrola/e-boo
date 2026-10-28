# Ubuntu Lab Manager — Setup & Installation Guide

This guide walks you through setting up Ubuntu Lab Manager on your central always-on PC and deploying the client agent across your 10 Ubuntu PCs.

---

## Prerequisites
- **1 Central PC** (Ubuntu 20.04/22.04/24.04, Debian, or Windows with Python 3.10+ and Node.js 18+).
- **10 Ubuntu Client PCs** with existing administrator accounts and SSH enabled.
- Stable LAN IP addresses or DHCP reservations (e.g. Server at `192.168.1.50`, PCs at `192.168.1.101` – `192.168.1.110`).

---

## Phase 1: Setup Central Server

### 1. Initialize Python Environment & Dependencies
```bash
# In repository root
python3 -m venv venv
source venv/bin/activate  # Or .\venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
```

### 2. Generate LAN TLS Certificates
Generate Root CA and server certificates matching your central server's LAN IP:
```bash
python scripts/generate_certs.py --ip 192.168.1.50 --hostname lab-server.local
```
This produces:
- `certs/ca.crt` & `certs/ca.key` (Root Certificate Authority)
- `certs/server.crt` & `certs/server.key` (Signed Server Certificate with SAN)

### 3. Initialize Database & Seed Administrator
Run the bootstrap script:
```bash
python scripts/setup_server.py --admin-user admin --admin-password "YourStrongPass123!"
```
This creates:
- SQLite schema with WAL mode enabled (`lab_manager.db`)
- Default permission profiles: `Student`, `Lab Assistant`, `Administrator`
- Initial administrator account
- Initial 10-PC enrollment token (e.g., `enroll_lab_xxxxxxxx`)

### 4. Build and Run Frontend
```bash
cd frontend
npm run build
npm run start -- -p 3000 -H 0.0.0.0
```

### 5. Run Central Backend Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
Or for production systemd deployment:
```bash
sudo cp deployment/systemd/ubuntu-lab-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ubuntu-lab-manager
```

---

## Phase 2: Deploy Agent to 10 Ubuntu PCs

### Method A: Automated Controlled Bootstrap Script (Recommended)
Edit `lab_hosts.txt` with your 10 PC addresses:
```text
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
```
Execute mass bootstrap:
```bash
bash scripts/bootstrap_lab.sh https://192.168.1.50:8000 <YOUR_ENROLLMENT_TOKEN> lab_hosts.txt
```

### Method B: Manual One-Line PC Installation
Log into an individual Ubuntu PC and run:
```bash
sudo bash scripts/install_agent.sh \
  --server https://192.168.1.50:8000 \
  --token <YOUR_ENROLLMENT_TOKEN> \
  --hostname LAB-PC-01 \
  --ca-cert certs/ca.crt
```
The script:
1. Installs agent files into `/opt/ubuntu-lab-manager/agent`.
2. Registers device with the server, receiving a unique device token.
3. Installs and enables `ubuntu-lab-agent.service`.
4. Starts sending heartbeats every 15 seconds.

---

## Phase 3: Accessing the Dashboard

Open your browser from any PC on the LAN:
```
https://192.168.1.50:3000
```
Log in using your administrator credentials. All 10 registered PCs will immediately appear as **Online** on the dashboard.
