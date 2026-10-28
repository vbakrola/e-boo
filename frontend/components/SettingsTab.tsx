"use client";

import React, { useState, useEffect } from "react";
import {
  Settings,
  HardDrive,
  Key,
  Download,
  Copy,
  Check,
  Plus,
  Trash2,
  ShieldCheck,
  Server,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { EnrollmentToken, getBaseApiUrl, api } from "../lib/api";

export default function SettingsTab() {
  const [tokens, setTokens] = useState<EnrollmentToken[]>([]);
  const [isLoadingTokens, setIsLoadingTokens] = useState(true);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  // New Token Modal
  const [showNewTokenModal, setShowNewTokenModal] = useState(false);
  const [tokenLabel, setTokenLabel] = useState("10-PC Lab Enrollment");
  const [maxUses, setMaxUses] = useState(15);
  const [expiresInHours, setExpiresInHours] = useState(48);
  const [isGenerating, setIsGenerating] = useState(false);

  // Backup State
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [backupResult, setBackupResult] = useState<{
    filename: string;
    backup_path: string;
    size_bytes: number;
    created_at: string;
  } | null>(null);

  const apiUrl = getBaseApiUrl();

  const fetchTokens = async () => {
    setIsLoadingTokens(true);
    try {
      const data = await api.getEnrollmentTokens();
      setTokens(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoadingTokens(false);
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  const handleCreateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    try {
      await api.createEnrollmentToken(tokenLabel, maxUses, expiresInHours);
      setShowNewTokenModal(false);
      fetchTokens();
    } catch (err: any) {
      alert(`Error creating enrollment token: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRevokeToken = async (id: number) => {
    if (!confirm("Are you sure you want to revoke this enrollment token?")) return;
    try {
      await api.revokeEnrollmentToken(id);
      fetchTokens();
    } catch (err: any) {
      alert(`Error revoking token: ${err.message}`);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(text);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const handleTriggerBackup = async () => {
    setIsBackingUp(true);
    try {
      const res = await api.backupDatabase();
      setBackupResult(res);
    } catch (err: any) {
      alert(`Backup error: ${err.message}`);
    } finally {
      setIsBackingUp(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
          System Settings & Lab Infrastructure
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
          Configure LAN networking, device enrollment keys, TLS certificates, and database backups
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "1.5rem" }}>
        {/* LAN Server Configuration */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{ padding: "0.6rem", borderRadius: "10px", background: "rgba(56, 189, 248, 0.12)", color: "var(--accent-sky)" }}>
              <Server size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>LAN Central Server</h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Offline isolated deployment configuration</p>
            </div>
          </div>

          <div style={{ background: "var(--bg-secondary)", borderRadius: "8px", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.825rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Server API Base URL:</span>
              <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{apiUrl}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Dashboard Port:</span>
              <span style={{ fontFamily: "var(--font-mono)" }}>3000 (HTTPS/HTTP)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Backend Port:</span>
              <span style={{ fontFamily: "var(--font-mono)" }}>8000</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Heartbeat Timeout:</span>
              <span>45 seconds</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Storage Engine:</span>
              <span>SQLite with WAL mode</span>
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.35rem" }}>
              Agent Bootstrap Command
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
              Run on target Ubuntu PC with your active enrollment token:
            </p>
            <div
              style={{
                background: "rgba(0, 0, 0, 0.5)",
                padding: "0.65rem 0.85rem",
                borderRadius: "6px",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                color: "var(--accent-sky)",
                border: "1px solid var(--border-subtle)",
                wordBreak: "break-all",
              }}
            >
              sudo bash scripts/install_agent.sh --server {apiUrl} --token &lt;TOKEN&gt; --hostname LAB-PC-01
            </div>
          </div>
        </div>

        {/* Database Online Backup */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{ padding: "0.6rem", borderRadius: "10px", background: "rgba(16, 185, 129, 0.12)", color: "var(--accent-emerald)" }}>
              <HardDrive size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>Database Backup</h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Atomic snapshot without stopping the server</p>
            </div>
          </div>

          <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            Ubuntu Lab Manager uses SQLite's official online backup API to copy write-ahead logs and database tables safely without taking the lab manager offline or interrupting running tasks.
          </p>

          <button
            onClick={handleTriggerBackup}
            disabled={isBackingUp}
            className="btn btn-primary"
            style={{ alignSelf: "flex-start" }}
          >
            <Download size={15} />
            <span>{isBackingUp ? "Creating Online Backup..." : "Create Database Backup Now"}</span>
          </button>

          {backupResult && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: "8px",
                padding: "0.85rem",
                fontSize: "0.8rem",
              }}
            >
              <div style={{ color: "#34d399", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.35rem", marginBottom: "0.35rem" }}>
                <Check size={16} />
                <span>Backup Created Successfully!</span>
              </div>
              <div style={{ color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.75rem" }}>
                <div><strong>Filename:</strong> {backupResult.filename}</div>
                <div><strong>Size:</strong> {(backupResult.size_bytes / 1024).toFixed(1)} KB</div>
                <div><strong>Path:</strong> <span style={{ fontFamily: "var(--font-mono)" }}>{backupResult.backup_path}</span></div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Device Enrollment Tokens */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Device Enrollment Tokens</h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Time-limited authorization tokens used by Python agents to register client workstations
            </p>
          </div>

          <button onClick={() => setShowNewTokenModal(true)} className="btn btn-primary">
            <Plus size={15} />
            <span>Generate New Token</span>
          </button>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.825rem", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-medium)" }}>
                <th style={{ padding: "0.75rem 1rem" }}>Label</th>
                <th style={{ padding: "0.75rem 1rem" }}>Token</th>
                <th style={{ padding: "0.75rem 1rem" }}>Usage Limit</th>
                <th style={{ padding: "0.75rem 1rem" }}>Status</th>
                <th style={{ padding: "0.75rem 1rem" }}>Expires</th>
                <th style={{ padding: "0.75rem 1rem", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((tok) => {
                const isCopied = copiedToken === tok.token;

                return (
                  <tr key={tok.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "0.75rem 1rem", fontWeight: 600 }}>{tok.label}</td>
                    <td style={{ padding: "0.75rem 1rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <code style={{ fontFamily: "var(--font-mono)", color: "var(--accent-sky)", fontSize: "0.78rem" }}>
                          {tok.token.slice(0, 16)}...
                        </code>
                        <button
                          onClick={() => handleCopy(tok.token)}
                          className="btn btn-secondary"
                          style={{ padding: "0.2rem 0.4rem", fontSize: "0.7rem" }}
                          title="Copy full token"
                        >
                          {isCopied ? <Check size={12} style={{ color: "#34d399" }} /> : <Copy size={12} />}
                        </button>
                      </div>
                    </td>
                    <td style={{ padding: "0.75rem 1rem" }}>
                      {tok.uses_count} of {tok.max_uses} PCs
                    </td>
                    <td style={{ padding: "0.75rem 1rem" }}>
                      {tok.is_active ? (
                        <span className="badge badge-online">Active</span>
                      ) : (
                        <span className="badge badge-offline">Revoked / Expired</span>
                      )}
                    </td>
                    <td style={{ padding: "0.75rem 1rem", color: "var(--text-muted)" }}>
                      {new Date(tok.expires_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: "0.75rem 1rem", textAlign: "right" }}>
                      {tok.is_active && (
                        <button
                          onClick={() => handleRevokeToken(tok.id)}
                          className="btn btn-secondary"
                          style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem", color: "var(--accent-rose)" }}
                          title="Revoke Token"
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* New Token Modal */}
      {showNewTokenModal && (
        <div className="modal-overlay" onClick={() => setShowNewTokenModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: "1.75rem" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Generate Device Enrollment Token
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Tokens authorize client Ubuntu workstations to register themselves into the lab dashboard.
            </p>

            <form onSubmit={handleCreateToken} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label className="form-label">Token Label</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  value={tokenLabel}
                  onChange={(e) => setTokenLabel(e.target.value)}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label className="form-label">Maximum Device Uses</label>
                  <input
                    type="number"
                    className="form-input"
                    min={1}
                    max={50}
                    value={maxUses}
                    onChange={(e) => setMaxUses(Number(e.target.value))}
                  />
                </div>

                <div>
                  <label className="form-label">Expiration (Hours)</label>
                  <input
                    type="number"
                    className="form-input"
                    min={1}
                    max={720}
                    value={expiresInHours}
                    onChange={(e) => setExpiresInHours(Number(e.target.value))}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
                <button
                  type="button"
                  onClick={() => setShowNewTokenModal(false)}
                  className="btn btn-secondary"
                  disabled={isGenerating}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isGenerating}>
                  {isGenerating ? "Generating..." : "Generate Token"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
