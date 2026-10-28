"use client";

import React, { useState } from "react";
import {
  Monitor,
  CheckCircle2,
  Users,
  Activity,
  AlertTriangle,
  RefreshCw,
  Search,
  ExternalLink,
  Edit2,
  Trash2,
  Cpu,
  Clock,
  Shield,
  UserPlus,
  Terminal,
} from "lucide-react";
import { Device, DashboardSummary, api } from "../lib/api";

interface OverviewTabProps {
  summary: DashboardSummary | null;
  devices: Device[];
  onRefresh: () => void;
  onNavigateToBulk: (targetHostname?: string) => void;
  onNavigateToTasks: () => void;
}

export default function OverviewTab({
  summary,
  devices,
  onRefresh,
  onNavigateToBulk,
  onNavigateToTasks,
}: OverviewTabProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "online" | "offline">("all");
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [editHostname, setEditHostname] = useState("");
  const [editIp, setEditIp] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Filter devices
  const filteredDevices = devices.filter((dev) => {
    const matchesSearch =
      dev.hostname.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dev.ip_address.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "online" && dev.status === "online") ||
      (statusFilter === "offline" && dev.status !== "online");
    return matchesSearch && matchesStatus;
  });

  const totalPCs = devices.length;
  const onlinePCs = devices.filter((d) => d.status === "online").length;

  const handleOpenEdit = (dev: Device) => {
    setEditingDevice(dev);
    setEditHostname(dev.hostname);
    setEditIp(dev.ip_address);
  };

  const handleSaveDevice = async () => {
    if (!editingDevice) return;
    setIsSaving(true);
    try {
      await api.updateDevice(editingDevice.id, {
        hostname: editHostname.trim(),
        ip_address: editIp.trim(),
      });
      setEditingDevice(null);
      onRefresh();
    } catch (err: any) {
      alert(`Error updating device: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteDevice = async (dev: Device) => {
    if (!confirm(`Are you sure you want to deregister device '${dev.hostname}'?`)) return;
    try {
      await api.deleteDevice(dev.id);
      onRefresh();
    } catch (err: any) {
      alert(`Error removing device: ${err.message}`);
    }
  };

  const formatRelativeTime = (isoString?: string) => {
    if (!isoString) return "Never";
    const date = new Date(isoString);
    const diffSeconds = Math.round((new Date().getTime() - date.getTime()) / 1000);
    if (diffSeconds < 10) return "Just now";
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    return `${Math.floor(diffMinutes / 60)}h ago`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Header & Controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Computer Laboratory Overview
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            Real-time status of 10 Ubuntu workstations connected to the private LAN
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button onClick={onRefresh} className="btn btn-secondary">
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
          <button onClick={() => onNavigateToBulk()} className="btn btn-primary">
            <UserPlus size={16} />
            <span>Bulk User Creation</span>
          </button>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1rem",
        }}
      >
        {/* Total PCs */}
        <div className="card" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div
            style={{
              padding: "0.75rem",
              borderRadius: "12px",
              background: "rgba(56, 189, 248, 0.12)",
              color: "var(--accent-sky)",
            }}
          >
            <Monitor size={24} />
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 500 }}>
              Total Lab PCs
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>{totalPCs} / 10</div>
          </div>
        </div>

        {/* Online PCs */}
        <div className="card" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div
            style={{
              padding: "0.75rem",
              borderRadius: "12px",
              background: "rgba(16, 185, 129, 0.12)",
              color: "var(--accent-emerald)",
            }}
          >
            <CheckCircle2 size={24} />
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 500 }}>
              Online PCs
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700, color: "#34d399" }}>
              {onlinePCs}
            </div>
          </div>
        </div>

        {/* Managed Users */}
        <div className="card" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div
            style={{
              padding: "0.75rem",
              borderRadius: "12px",
              background: "rgba(6, 182, 212, 0.12)",
              color: "var(--accent-cyan)",
            }}
          >
            <Users size={24} />
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 500 }}>
              Managed Users
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
              {summary?.total_managed_users ?? 0}
            </div>
          </div>
        </div>

        {/* Running Tasks */}
        <div
          className="card"
          style={{ display: "flex", alignItems: "center", gap: "1rem", cursor: "pointer" }}
          onClick={onNavigateToTasks}
        >
          <div
            style={{
              padding: "0.75rem",
              borderRadius: "12px",
              background: "rgba(99, 102, 241, 0.12)",
              color: "var(--accent-indigo)",
            }}
          >
            <Activity size={24} />
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 500 }}>
              Running Tasks
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--accent-sky)" }}>
              {summary?.running_tasks ?? 0}
            </div>
          </div>
        </div>

        {/* Failed Tasks */}
        <div
          className="card"
          style={{ display: "flex", alignItems: "center", gap: "1rem", cursor: "pointer" }}
          onClick={onNavigateToTasks}
        >
          <div
            style={{
              padding: "0.75rem",
              borderRadius: "12px",
              background: "rgba(239, 68, 68, 0.12)",
              color: "var(--accent-rose)",
            }}
          >
            <AlertTriangle size={24} />
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 500 }}>
              Failed Tasks
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700, color: summary?.failed_tasks ? "var(--accent-rose)" : "var(--text-muted)" }}>
              {summary?.failed_tasks ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, minWidth: "260px" }}>
          <div style={{ position: "relative", width: "100%", maxWidth: "340px" }}>
            <Search
              size={16}
              style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }}
            />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: "2.25rem" }}
              placeholder="Search hostname or IP address..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", background: "var(--bg-card)", padding: "0.2rem", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
            <button
              onClick={() => setStatusFilter("all")}
              className="btn btn-secondary"
              style={{
                fontSize: "0.75rem",
                padding: "0.25rem 0.65rem",
                border: "none",
                background: statusFilter === "all" ? "var(--bg-surface)" : "transparent",
                color: statusFilter === "all" ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              All ({devices.length})
            </button>
            <button
              onClick={() => setStatusFilter("online")}
              className="btn btn-secondary"
              style={{
                fontSize: "0.75rem",
                padding: "0.25rem 0.65rem",
                border: "none",
                background: statusFilter === "online" ? "var(--bg-surface)" : "transparent",
                color: statusFilter === "online" ? "#34d399" : "var(--text-muted)",
              }}
            >
              Online ({onlinePCs})
            </button>
            <button
              onClick={() => setStatusFilter("offline")}
              className="btn btn-secondary"
              style={{
                fontSize: "0.75rem",
                padding: "0.25rem 0.65rem",
                border: "none",
                background: statusFilter === "offline" ? "var(--bg-surface)" : "transparent",
                color: statusFilter === "offline" ? "#f87171" : "var(--text-muted)",
              }}
            >
              Offline ({devices.length - onlinePCs})
            </button>
          </div>
        </div>

        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Showing {filteredDevices.length} of {devices.length} workstations
        </div>
      </div>

      {/* 10-PC Workstations Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(290px, 1fr))",
          gap: "1.25rem",
        }}
      >
        {filteredDevices.map((dev) => {
          const isOnline = dev.status === "online";

          return (
            <div
              key={dev.id}
              className="card"
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "1rem",
                background: isOnline ? "var(--bg-surface)" : "rgba(17, 28, 53, 0.4)",
                borderColor: isOnline ? "rgba(56, 189, 248, 0.2)" : "var(--border-subtle)",
              }}
            >
              {/* Card Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontWeight: 700, fontSize: "1.05rem", fontFamily: "var(--font-mono)" }}>
                      {dev.hostname}
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.8rem",
                      color: "var(--accent-sky)",
                      marginTop: "0.2rem",
                    }}
                  >
                    {dev.ip_address}
                  </div>
                </div>

                <span className={`badge badge-${isOnline ? "online" : "offline"}`}>
                  <span className={`status-dot status-dot-${isOnline ? "online" : "offline"}`} />
                  {isOnline ? "Online" : "Offline"}
                </span>
              </div>

              {/* Specs & Vitals */}
              <div
                style={{
                  background: "var(--bg-secondary)",
                  borderRadius: "8px",
                  padding: "0.65rem 0.85rem",
                  fontSize: "0.75rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.35rem",
                  color: "var(--text-secondary)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>OS Release:</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{dev.os_version}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Agent Version:</span>
                  <span style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                    v{dev.agent_version}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Last Heartbeat:</span>
                  <span style={{ color: isOnline ? "#34d399" : "var(--accent-rose)", fontWeight: 500 }}>
                    {formatRelativeTime(dev.last_heartbeat_at)}
                  </span>
                </div>
              </div>

              {/* Actions Footer */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  borderTop: "1px solid var(--border-subtle)",
                  paddingTop: "0.75rem",
                }}
              >
                <button
                  onClick={() => onNavigateToBulk(dev.hostname)}
                  className="btn btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "0.3rem 0.6rem" }}
                  title="Provision user specifically for this PC"
                >
                  <UserPlus size={14} />
                  <span>Provision</span>
                </button>

                <div style={{ display: "flex", gap: "0.4rem" }}>
                  <button
                    onClick={() => handleOpenEdit(dev)}
                    className="btn btn-secondary"
                    style={{ padding: "0.35rem", color: "var(--text-muted)" }}
                    title="Edit Hostname / IP"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button
                    onClick={() => handleDeleteDevice(dev)}
                    className="btn btn-secondary"
                    style={{ padding: "0.35rem", color: "var(--accent-rose)" }}
                    title="Deregister device"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* If 0 devices or empty lab */}
      {devices.length === 0 && (
        <div
          className="card"
          style={{
            textAlign: "center",
            padding: "3rem 1.5rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <Monitor size={48} style={{ color: "var(--text-muted)" }} />
          <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>No Ubuntu PCs Enrolled Yet</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", maxWidth: "480px" }}>
            To enroll your 10 lab computers, run the bootstrap script from the central server or install the lightweight agent on each machine using an enrollment token.
          </p>
        </div>
      )}

      {/* Edit Device Modal */}
      {editingDevice && (
        <div className="modal-overlay" onClick={() => setEditingDevice(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: "1.75rem" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Configure Workstation
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Update network hostname and LAN IP reservation for this Ubuntu client.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label className="form-label">Hostname</label>
                <input
                  type="text"
                  className="form-input"
                  value={editHostname}
                  onChange={(e) => setEditHostname(e.target.value)}
                />
              </div>

              <div>
                <label className="form-label">LAN IP Address</label>
                <input
                  type="text"
                  className="form-input"
                  value={editIp}
                  onChange={(e) => setEditIp(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
              <button onClick={() => setEditingDevice(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={handleSaveDevice} disabled={isSaving} className="btn btn-primary">
                {isSaving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
