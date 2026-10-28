"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  Search,
  RefreshCw,
  Shield,
  User,
  Clock,
  ExternalLink,
} from "lucide-react";
import { AuditLog, api } from "../lib/api";

export default function AuditLogsTab() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAuditLogs(actionFilter || undefined, 100);
      setLogs(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [actionFilter]);

  const formatTimestamp = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Security Audit Trail
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            Immutable administrative event logging with automatic credential redaction
          </p>
        </div>

        <button onClick={fetchLogs} className="btn btn-secondary">
          <RefreshCw size={15} />
          <span>Refresh Logs</span>
        </button>
      </div>

      {/* Filter */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          background: "var(--bg-surface)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, maxWidth: "360px" }}>
          <div style={{ position: "relative", width: "100%" }}>
            <Search
              size={16}
              style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }}
            />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: "2.25rem" }}
              placeholder="Filter by action (e.g. LOGIN, BATCH, USER)..."
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
          </div>
        </div>

        <div style={{ fontSize: "0.825rem", color: "var(--text-muted)" }}>
          Showing latest {logs.length} audit trail records
        </div>
      </div>

      {/* Audit Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-medium)" }}>
              <th style={{ padding: "0.85rem 1rem" }}>Timestamp</th>
              <th style={{ padding: "0.85rem 1rem" }}>Administrator</th>
              <th style={{ padding: "0.85rem 1rem" }}>Action</th>
              <th style={{ padding: "0.85rem 1rem" }}>Target Entity</th>
              <th style={{ padding: "0.85rem 1rem" }}>IP Address</th>
              <th style={{ padding: "0.85rem 1rem", textAlign: "right" }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && logs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                  <RefreshCw className="animate-spin" size={24} style={{ margin: "0 auto 0.5rem" }} />
                  <div>Loading audit logs...</div>
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                  <FileText size={32} style={{ margin: "0 auto 0.5rem", opacity: 0.5 }} />
                  <div>No audit trail events match the current filter.</div>
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "0.85rem 1rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                    {formatTimestamp(log.created_at)}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", fontWeight: 600 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <User size={14} style={{ color: "var(--accent-sky)" }} />
                      <span>{log.admin_username || "system"}</span>
                    </div>
                  </td>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    <span
                      style={{
                        padding: "0.15rem 0.45rem",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                        background: log.action.includes("FAIL")
                          ? "rgba(239, 68, 68, 0.15)"
                          : log.action.includes("SUCCESS") || log.action.includes("CREATED")
                          ? "rgba(16, 185, 129, 0.15)"
                          : "rgba(56, 189, 248, 0.15)",
                        color: log.action.includes("FAIL")
                          ? "var(--accent-rose)"
                          : log.action.includes("SUCCESS") || log.action.includes("CREATED")
                          ? "#34d399"
                          : "var(--accent-sky)",
                      }}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td style={{ padding: "0.85rem 1rem", color: "var(--text-secondary)" }}>
                    {log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ""}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    {log.ip_address || "127.0.0.1"}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", textAlign: "right" }}>
                    {log.details_json ? (
                      <button
                        onClick={() => setSelectedLog(log)}
                        className="btn btn-secondary"
                        style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                      >
                        Inspect
                      </button>
                    ) : (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Log Details Modal */}
      {selectedLog && (
        <div className="modal-overlay" onClick={() => setSelectedLog(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: "1.75rem" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Audit Event Payload
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Action: <code style={{ color: "var(--accent-sky)" }}>{selectedLog.action}</code> • User: {selectedLog.admin_username}
            </p>

            <pre
              style={{
                background: "var(--bg-secondary)",
                padding: "1rem",
                borderRadius: "8px",
                fontSize: "0.8rem",
                fontFamily: "var(--font-mono)",
                whiteSpace: "pre-wrap",
                maxHeight: "300px",
                overflowY: "auto",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {(() => {
                try {
                  return JSON.stringify(JSON.parse(selectedLog.details_json || "{}"), null, 2);
                } catch {
                  return selectedLog.details_json;
                }
              })()}
            </pre>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1.5rem" }}>
              <button onClick={() => setSelectedLog(null)} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
