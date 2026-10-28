"use client";

import React, { useState, useEffect, useCallback } from "react";
import Navbar from "../components/Navbar";
import Sidebar, { TabType } from "../components/Sidebar";
import OverviewTab from "../components/OverviewTab";
import BulkProvisioningTab from "../components/BulkProvisioningTab";
import UserManagementTab from "../components/UserManagementTab";
import ProfilesTab from "../components/ProfilesTab";
import TaskProgressTab from "../components/TaskProgressTab";
import AuditLogsTab from "../components/AuditLogsTab";
import SettingsTab from "../components/SettingsTab";
import LoginModal from "../components/LoginModal";
import ChangePasswordModal from "../components/ChangePasswordModal";
import {
  AdminUser,
  Device,
  PermissionProfile,
  DashboardSummary,
  getAuthToken,
  setAuthToken,
  api,
} from "../lib/api";

export default function Home() {
  const [adminUser, setAdminUser] = useState<AdminUser | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [currentTab, setCurrentTab] = useState<TabType>("overview");

  // Core Data
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [profiles, setProfiles] = useState<PermissionProfile[]>([]);

  // Controls & Modals
  const [isLiveRefreshing, setIsLiveRefreshing] = useState(true);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [bulkTargetHostname, setBulkTargetHostname] = useState<string | undefined>(undefined);

  // Load all dashboard data
  const loadDashboardData = useCallback(async () => {
    try {
      const [sumData, devData, profData] = await Promise.all([
        api.getSummary().catch(() => null),
        api.getDevices().catch(() => []),
        api.getProfiles().catch(() => []),
      ]);

      if (sumData) setSummary(sumData);
      if (devData) setDevices(devData);
      if (profData) setProfiles(profData);
    } catch (err) {
      console.error("Dashboard refresh error:", err);
    }
  }, []);

  // Check login on startup
  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      api
        .getMe()
        .then((user) => {
          setAdminUser(user);
          loadDashboardData();
        })
        .catch(() => {
          setAuthToken(null);
          setAdminUser(null);
        })
        .finally(() => setIsInitializing(false));
    } else {
      setIsInitializing(false);
    }

    const handleLogoutEvent = () => setAdminUser(null);
    window.addEventListener("auth:logout", handleLogoutEvent);
    return () => window.removeEventListener("auth:logout", handleLogoutEvent);
  }, [loadDashboardData]);

  // Periodic live sync (every 5 seconds)
  useEffect(() => {
    if (!adminUser || !isLiveRefreshing) return;

    const interval = setInterval(() => {
      loadDashboardData();
    }, 5000);

    return () => clearInterval(interval);
  }, [adminUser, isLiveRefreshing, loadDashboardData]);

  const handleLoginSuccess = (user: AdminUser) => {
    setAdminUser(user);
    loadDashboardData();
  };

  const handleLogout = () => {
    setAuthToken(null);
    setAdminUser(null);
  };

  const handleNavigateToBulk = (targetHostname?: string) => {
    setBulkTargetHostname(targetHostname);
    setCurrentTab("bulk");
  };

  if (isInitializing) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          backgroundColor: "var(--bg-primary)",
          color: "var(--text-secondary)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>Loading Ubuntu Lab Manager...</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Connecting to LAN management daemon
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Login Screen if not authenticated */}
      {!adminUser && <LoginModal onLoginSuccess={handleLoginSuccess} />}

      {/* Main Authenticated Dashboard */}
      {adminUser && (
        <>
          <Navbar
            adminUser={adminUser}
            onOpenPasswordModal={() => setShowPasswordModal(true)}
            onLogout={handleLogout}
            isLiveRefreshing={isLiveRefreshing}
            onToggleLiveRefresh={() => setIsLiveRefreshing((prev) => !prev)}
          />

          <div style={{ display: "flex", flex: 1 }}>
            <Sidebar
              currentTab={currentTab}
              onSelectTab={setCurrentTab}
              onlineCount={devices.filter((d) => d.status === "online").length}
              totalDevices={devices.length}
              runningTasksCount={summary?.running_tasks ?? 0}
            />

            <main
              style={{
                flex: 1,
                padding: "2rem",
                maxWidth: "1400px",
                margin: "0 auto",
                width: "100%",
              }}
            >
              {currentTab === "overview" && (
                <OverviewTab
                  summary={summary}
                  devices={devices}
                  onRefresh={loadDashboardData}
                  onNavigateToBulk={handleNavigateToBulk}
                  onNavigateToTasks={() => setCurrentTab("tasks")}
                />
              )}

              {currentTab === "bulk" && (
                <BulkProvisioningTab
                  devices={devices}
                  profiles={profiles}
                  initialSelectedHost={bulkTargetHostname}
                  onRefreshDevices={loadDashboardData}
                />
              )}

              {currentTab === "users" && (
                <UserManagementTab
                  devices={devices}
                  onRefreshDevices={loadDashboardData}
                />
              )}

              {currentTab === "profiles" && (
                <ProfilesTab
                  profiles={profiles}
                  onRefreshProfiles={loadDashboardData}
                />
              )}

              {currentTab === "tasks" && (
                <TaskProgressTab
                  devices={devices}
                  onRefreshDevices={loadDashboardData}
                />
              )}

              {currentTab === "audit" && <AuditLogsTab />}

              {currentTab === "settings" && <SettingsTab />}
            </main>
          </div>

          {/* Change Password Modal */}
          {showPasswordModal && (
            <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />
          )}
        </>
      )}
    </div>
  );
}
