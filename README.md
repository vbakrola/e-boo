# Ubuntu Lab Manager — LAN-Only Application

**Ubuntu Lab Manager** is a complete, self-contained, LAN-only web application and agent daemon designed to manage Linux user accounts across 10 Ubuntu workstations connected to the same local Ethernet or Wi-Fi network.

The system is built for complete offline privacy: **zero cloud services, no external identity providers, and zero telemetry**. All communication stays inside your local laboratory network over encrypted, authenticated channels.

---

## 1. Technology Stack

| Layer | Technology | Key Capabilities |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 + TypeScript (App Router) | Modern dark navy/slate dashboard, real-time status indicators, interactive grid, CSV import with row diagnostics |
| **Backend** | Python 3.11 + FastAPI + Uvicorn | Async REST API, background worker, JWT sessions, security headers |
| **Database** | SQLite with WAL Mode + SQLAlchemy + Alembic | Zero-config, ACID-compliant, concurrent reads/writes via Write-Ahead-Logging |
| **Client Agent** | Native Python 3 systemd daemon | **Zero third-party dependencies** (stdlib `urllib`, `ssl`, `subprocess`), auto-restart on network glitch |
| **Security** | Argon2id + AES-256-GCM Ephemeral Envelopes | Memory-hard password hashing, secret redaction in audit trails, fixed POSIX argument arrays (`shell=False`) |

---

## 2. Main Use Case: Simultaneous Multi-PC User Creation

From a single browser dashboard on your LAN (e.g., `https://192.168.1.50:3000`), you can provision distinct user accounts across all 10 Ubuntu PCs in a single operation:

```
Workstation   Target Username   Initial Password      Role Profile      1st Login Expiry
----------------------------------------------------------------------------------------
LAB-PC-01     student101        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-02     student102        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-03     student103        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-04     student104        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-05     student105        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-06     student106        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-07     student107        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-08     student108        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-09     student109        [Individual Secret]   Student           Yes (passwd -e)
LAB-PC-10     labassistant1     [Individual Secret]   Lab Assistant     No
```

---

## 3. Architecture & Security Safeguards

### Ephemeral Credential Envelopes (Zero Plaintext Storage)
- Passwords are **never stored in plaintext** in the database or logs.
- Initial credentials are encrypted into an ephemeral **AES-256-GCM** envelope with a 10-minute TTL.
- When an authorized agent polls its task over TLS, the envelope is decrypted in-flight and **permanently deleted from the database immediately**.
- On the Ubuntu PC, the agent pipes the password directly into `/usr/sbin/chpasswd` via `stdin`—it is never passed in command-line arguments (`argv`), eliminating exposure in `ps aux` or shell histories.

### Strict Injection Prevention & Fixed Command Set
- No arbitrary shell commands are accepted by the server or agent.
- Permitted operations are fixed: `CREATE_USER`, `RESET_PASSWORD`, `LOCK_ACCOUNT`, `UNLOCK_ACCOUNT`, `SET_ACCOUNT_EXPIRY`, `DELETE_USER`.
- System commands are executed strictly as argument arrays with `shell=False`.

### Protected Account Safelist
The application enforces a hardcoded safeguard preventing modification, password reset, locking, or deletion of crucial system and administrative accounts:
`root`, `ubuntu`, `admin`, `administrator`, `sudo`, `sys`, `daemon`, `bin`, `sync`, `games`, `man`, `lp`, `mail`, `news`, `uucp`, `proxy`, `www-data`, `backup`, `list`, `irc`, `gnats`, `nobody`, `systemd-*`, `sshd`.

### Offline Workstation Resilience
If one or more workstations are powered off or disconnected during bulk provisioning:
- Online workstations execute their tasks immediately without delay.
- Offline workstations' tasks remain safely in the `QUEUED` state and execute automatically as soon as the workstation boots up and reconnects.
- Failed tasks can be safely retried individually with one click.

---

## 4. Repository Structure

```
ubuntu-lab-manager/
├── backend/
│   ├── app/
│   │   ├── config.py         # Settings & protected accounts safelist
│   │   ├── database.py       # SQLite connection with WAL mode
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── schemas.py        # Pydantic validation schemas
│   │   ├── security.py       # Argon2id, JWT, AES-256-GCM, POSIX validation
│   │   ├── worker.py         # Background heartbeat monitor & queue worker
│   │   ├── main.py           # FastAPI entrypoint & security middleware
│   │   └── routers/          # API endpoints (auth, devices, provisioning, etc.)
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── globals.css       # Dark navy/slate theme design system
│   │   ├── layout.tsx        # Responsive root layout
│   │   └── page.tsx          # Main dashboard coordinator
│   ├── components/           # UI components (Overview, Bulk, Users, Profiles, etc.)
│   └── lib/api.ts            # Typed API client
├── agent/
│   ├── agent.py              # Zero-dependency client daemon
│   ├── config.py             # Agent config with 0600 file permission enforcement
│   ├── executor.py           # Local execution engine (shell=False, stdin piping)
│   └── system_info.py        # Hardware diagnostics & vitals collector
├── deployment/
│   └── systemd/              # Native systemd units for agent and server
├── migrations/               # Alembic database migrations
├── scripts/
│   ├── setup_server.py       # Database initialization & initial admin creation
│   ├── generate_certs.py     # Local Root CA & server cert generator with SAN
│   ├── seed_demo_lab.py      # Pre-seeds 10 Ubuntu PCs for instant test drive
│   ├── backup_db.py          # Atomic online SQLite backup
│   ├── install_agent.sh      # Ubuntu PC agent installer
│   ├── bootstrap_lab.sh      # Controlled mass SSH deployment for 10 PCs
│   ├── uninstall_agent.sh    # Clean agent uninstaller
│   └── start_server.py       # Full-stack concurrent server launcher
├── tests/                    # Comprehensive 54-test automated test suite
├── docs/                     # Architectural, security, and setup documentation
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Quick Start Installation

### Step 1: Install Dependencies
```bash
# Set up Python virtual environment
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend && npm install && npm run build && cd ..
```

### Step 2: Generate LAN TLS Certificates
Generate a local Root CA and Server certificate with Subject Alternative Names (SAN) for your LAN IP (e.g. `192.168.1.50`):
```bash
python scripts/generate_certs.py --ip 192.168.1.50 --hostname lab-server.local
```

### Step 3: Initialize Database & Administrator
```bash
python scripts/setup_server.py --admin-user admin --admin-password "AdminSecurePass2026!"
```

*(Optional)* Seed 10 realistic Ubuntu demo workstations (`LAB-PC-01` through `LAB-PC-10`) to test-drive the UI immediately:
```bash
python scripts/seed_demo_lab.py
```

### Step 4: Start the Server
```bash
python scripts/start_server.py
```
Open your browser at:
```
http://localhost:3000   (or https://192.168.1.50:3000 from another PC on the LAN)
```
Sign in with:
- **Username**: `admin`
- **Password**: `AdminSecurePass2026!`

---

## 6. Deploying the Agent on Ubuntu Workstations

### Method A: Automated SSH Bootstrap (All 10 PCs)
Create `lab_hosts.txt` with your 10 PCs:
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
Execute bootstrap:
```bash
bash scripts/bootstrap_lab.sh https://192.168.1.50:8000 <ENROLLMENT_TOKEN> lab_hosts.txt
```

### Method B: Single PC Installation
On the individual Ubuntu PC:
```bash
sudo bash scripts/install_agent.sh \
  --server https://192.168.1.50:8000 \
  --token <ENROLLMENT_TOKEN> \
  --hostname LAB-PC-01
```

The agent installs as a native systemd unit:
```bash
sudo systemctl status ubuntu-lab-agent.service
```

---

## 7. Running the Automated Test Suite

Run the full pytest suite (covering authentication, device enrollment, POSIX validation, bulk provisioning, task lifecycles, and offline resilience):
```bash
.\venv\Scripts\pytest -v tests
```
Output:
```
======================== 54 passed, 1 warning in 9.35s ========================
```

---

## 8. Definition of Done Verification

| Requirement | Verified Status |
| :--- | :--- |
| **Open dashboard from another LAN PC** | Verified (Listens on `0.0.0.0:3000` & `0.0.0.0:8000` with CORS & LAN SAN certs) |
| **Register all 10 Ubuntu PCs** | Verified (Device enrollment API, heartbeat monitoring, and mass bootstrap script) |
| **Simultaneous multi-PC user creation** | Verified (Interactive grid & CSV import with row-level validation) |
| **Individual PC execution** | Verified (Per-device task polling with ephemeral credential delivery) |
| **Student role has no sudo** | Verified (Profile enforcement tests and agent executor tests) |
| **Offline PCs do not block others** | Verified (`tests/test_offline_handling.py` passes) |
| **Failed tasks can be retried** | Verified (`tests/test_tasks.py` and UI retry buttons) |
| **Zero plaintext passwords stored** | Verified (`tests/test_credential_security.py` passes) |
| **Real task results reporting** | Verified (Agent reports success/failure details and ManagedUser updates) |
| **Safe database backup** | Verified (`scripts/backup_db.py` uses SQLite online backup API with integrity checks) |
