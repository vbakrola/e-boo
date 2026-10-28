"use client";

import React from "react";
import {
  LayoutDashboard,
  UserPlus,
  Users,
  ShieldCheck,
  Activity,
  FileText,
  Settings,
  HardDrive,
} from "lucide-react";

export type TabType =
  | "overview"
  | "bulk"
  | "users"
  | "profiles"
  | "tasks"
  | "audit"
  | "settings";

interface SidebarProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  onlineCount: number;
  totalDevices: number;
  runningTasksCount: number;
}

export default function Sidebar({
  currentTab,
  onSelectTab,
  onlineCount,
  totalDevices,
  runningTasksCount,
}: SidebarProps) {
  const navItems = [
    {
      id: "overview" as TabType,
      label: "Overview (10 PCs)",
      icon: LayoutDashboard,
      badge: `${onlineCount}/${totalDevices || 10}`,
      badgeColor: onlineCount > 0 ? "rgba(16, 185, 129, 0.2)" : "rgba(100, 116, 139, 0.2)",
      badgeTextColor: onlineCount > 0 ? "#34d399" : "#94a3b8",
    },
    {
      id: "bulk" as TabType,
      label: "Bulk User Creation",
      icon: UserPlus,
    },
    {
      id: "users" as TabType,
      label: "User Management",
      icon: Users,
    },
    {
      id: "profiles" as TabType,
      label: "Permission Profiles",
      icon: ShieldCheck,
    },
    {
      id: "tasks" as TabType,
      label: "Task Progress",
      icon: Activity,
      badge: runningTasksCount > 0 ? `${runningTasksCount} active` : undefined,
      badgeColor: "rgba(56, 189, 248, 0.2)",
      badgeTextColor: "#38bdf8",
    },
    {
      id: "audit" as TabType,
      label: "Audit Logs",
      icon: FileText,
    },
    {
      id: "settings" as TabType,
      label: "System Settings",
      icon: Settings,
    },
  ];

  return (
    <aside
      style={{
        width: "250px",
        backgroundColor: "var(--bg-secondary)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        minHeight: "calc(100vh - 64px)",
        padding: "1.25rem 0.75rem",
      }}
    >
      <nav style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        <div
          style={{
            fontSize: "0.68rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--text-muted)",
            padding: "0.5rem 0.75rem",
          }}
        >
          Navigation
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.65rem 0.85rem",
                borderRadius: "var(--radius-md)",
                backgroundColor: isActive ? "var(--bg-card)" : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                border: isActive ? "1px solid var(--border-medium)" : "1px solid transparent",
                fontWeight: isActive ? 600 : 500,
                fontSize: "0.85rem",
                cursor: "pointer",
                transition: "all 0.15s ease",
                textAlign: "left",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <Icon
                  size={18}
                  style={{
                    color: isActive ? "var(--accent-sky)" : "var(--text-muted)",
                  }}
                />
                <span>{item.label}</span>
              </div>

              {item.badge && (
                <span
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    padding: "0.15rem 0.45rem",
                    borderRadius: "9999px",
                    backgroundColor: item.badgeColor,
                    color: item.badgeTextColor,
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Mini Status Box */}
      <div
        className="card"
        style={{
          marginTop: "1.5rem",
          padding: "0.85rem",
          background: "rgba(10, 15, 29, 0.6)",
          borderColor: "var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
          <HardDrive size={15} style={{ color: "var(--accent-emerald)" }} />
          <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>Lab Status</span>
        </div>
        <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          <div>Isolated Local Network</div>
          <div>AES-256-GCM Ephemeral Envelopes</div>
          <div>SQLite WAL Synchronized</div>
        </div>
      </div>
    </aside>
  );
}
