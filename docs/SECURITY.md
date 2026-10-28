# Ubuntu Lab Manager — Security Architecture & Hardening

Ubuntu Lab Manager is designed for private local area networks with enterprise-grade defensive standards to prevent credential theft, unauthorized privilege escalation, and command injection.

---

## 1. Authentication & Session Security
- **Admin Password Storage**: Hashed using **Argon2id** (memory cost: 64MB, time cost: 3 iterations, 4 parallelism threads). Defends against GPU/ASIC cracking.
- **JWT Authorization**: Admin access tokens are cryptographically signed using HMAC-SHA256 with 8-hour expiration for lab class sessions.
- **Hardened HTTP Headers**: Responses automatically enforce:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 2. Independent Device Authentication
- Every Ubuntu PC is independently authenticated using a unique high-entropy device token (`dev_tok_...`) issued upon enrollment.
- Only the SHA-256 hash of the device token is persisted on the central server.
- Stolen or compromised PC tokens cannot impersonate other PCs or forge tasks.

---

## 3. Zero Plaintext Passwords & Ephemeral Envelopes
Passwords are treated as ephemeral sensitive secrets:
1. **Never Stored Plaintext**: Initial user passwords and password resets are never stored in plaintext in the database or logs.
2. **AES-256-GCM Envelope**: Encrypted with an ephemeral envelope having a 10-minute TTL.
3. **Wiped on Delivery**: As soon as the target PC retrieves the payload, the credential record is deleted from SQLite.
4. **Secure Piping**: The agent delivers passwords directly to `/usr/sbin/chpasswd` via standard input (`stdin`), preventing credentials from appearing in process listings (`ps aux`) or shell history.

---

## 4. Rejection of Arbitrary Shell Commands
- The API accepts only structured, fixed JSON action schemas:
  - `CREATE_USER`
  - `RESET_PASSWORD`
  - `LOCK_ACCOUNT`
  - `UNLOCK_ACCOUNT`
  - `SET_ACCOUNT_EXPIRY`
  - `DELETE_USER`
- System commands are executed with **explicit argument lists** and `shell=False`.
- Any command injection payload (e.g. `; rm -rf /`, `$(whoami)`, `` `id` ``) is rejected by POSIX username regex validation (`^[a-z_][a-z0-9_-]{0,31}$`).

---

## 5. System Administrator Protection Safelist
Built-in safeguard preventing modification or deletion of crucial system accounts:
`root`, `ubuntu`, `admin`, `administrator`, `sudo`, `sys`, `daemon`, `bin`, `sync`, `games`, `man`, `lp`, `mail`, `news`, `uucp`, `proxy`, `www-data`, `backup`, `list`, `irc`, `gnats`, `nobody`, `systemd-*`, `sshd`.
Destructive operations on any of these accounts are rejected immediately before execution.

---

## 6. Permission Profile Scoping
- **Student Profile**: Standard Linux account, bash shell, home directory, student group membership. **No sudo access**.
- **Lab Assistant Profile**: Standard Linux account. Sudo disabled by default.
- **Administrator Profile**: Restricted administrative profile according to explicit lab policy. Does not grant an unrestricted root shell or arbitrary `/etc/sudoers` editing through the web interface.
