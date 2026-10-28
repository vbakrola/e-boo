"use client";

import React from "react";
import { Server, Shield, Key, LogOut, Wifi, HardDrive } from "lucide-react";
import { AdminUser, getBaseApiUrl } from "../lib/api";

interface NavbarProps {
  adminUser: AdminUser | null;
  onOpenPasswordModal: () => void;
  onLogout: () => void;
  isLiveRefreshing: boolean;
  onToggleLiveRefresh: () => void;
}

export default function Navbar({
  adminUser,
  onOpenPasswordModal,
  onLogout,
  isLiveRefreshing,
  onToggleLiveRefresh,
}: NavbarProps) {
  const apiUrl = getBaseApiUrl();

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.875rem 1.75rem",
        backgroundColor: "var(--bg-secondary)",
        borderBottom: "1px solid var(--border-subtle)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Brand & LAN Badge */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "38px",
            height: "38px",
            borderRadius: "10px",
            background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
            color: "#ffffff",
            boxShadow: "0 0 15px rgba(2, 132, 199, 0.4)",
          }}
        >
          <Server size={22} />
        </div>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontWeight: 700, fontSize: "1.1rem", letterSpacing: "-0.01em" }}>
              Ubuntu Lab Manager
            </span>
            <span
              style={{
                fontSize: "0.68rem",
                fontWeight: 600,
                padding: "0.15rem 0.5rem",
                borderRadius: "4px",
                background: "rgba(56, 189, 248, 0.12)",
                color: "var(--accent-sky)",
                border: "1px solid rgba(56, 189, 248, 0.25)",
              }}
            >
              LAN ONLY
            </span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span>Central Management Server</span>
            <span>•</span>
            <span style={{ fontFamily: "var(--font-mono)" }}>{apiUrl}</span>
          </div>
        </div>
      </div>

      {/* Right controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        {/* Live Refresh Indicator */}
        <button
          onClick={onToggleLiveRefresh}
          className="btn btn-secondary"
          style={{
            fontSize: "0.75rem",
            padding: "0.35rem 0.75rem",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            borderColor: isLiveRefreshing ? "rgba(16, 185, 129, 0.4)" : "var(--border-subtle)",
          }}
          title={isLiveRefreshing ? "Live heartbeat polling enabled (every 5s)" : "Click to enable live polling"}
        >
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              backgroundColor: isLiveRefreshing ? "#10b981" : "#64748b",
              boxShadow: isLiveRefreshing ? "0 0 8px #10b981" : "none",
            }}
          />
          {isLiveRefreshing ? "Live Sync (5s)" : "Sync Paused"}
        </button>

        {/* Admin profile & actions */}
        {adminUser && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", borderLeft: "1px solid var(--border-subtle)", paddingLeft: "1rem" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.85rem", fontWeight: 600 }}>{adminUser.full_name}</div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>@{adminUser.username}</div>
            </div>

            <button
              onClick={onOpenPasswordModal}
              className="btn btn-secondary"
              style={{ padding: "0.45rem", color: "var(--text-secondary)" }}
              title="Change Password"
            >
              <Key size={16} />
            </button>

            <button
              onClick={onLogout}
              className="btn btn-secondary"
              style={{ padding: "0.45rem", color: "var(--accent-rose)" }}
              title="Log Out"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
