"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  Search,
  Filter,
  Lock,
  Unlock,
  Key,
  Calendar,
  Trash2,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import { ManagedUser, Device, api } from "../lib/api";

interface UserManagementTabProps {
  devices: Device[];
  onRefreshDevices: () => void;
}

export default function UserManagementTab({ devices, onRefreshDevices }: UserManagementTabProps) {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | undefined>(undefined);
  const [searchUsername, setSearchUsername] = useState("");

  // Action Modals
  const [activeModal, setActiveModal] = useState<"lock" | "unlock" | "reset" | "expiry" | "delete" | null>(null);
  const [targetUser, setTargetUser] = useState<ManagedUser | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [forcePasswordChange, setForcePasswordChange] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const data = await api.getManagedUsers(selectedDeviceId, searchUsername);
      setUsers(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [selectedDeviceId, searchUsername]);

  const handleOpenModal = (type: "lock" | "unlock" | "reset" | "expiry" | "delete", user: ManagedUser) => {
    setTargetUser(user);
    setActiveModal(type);
    setNewPassword("");
    setExpiryDate(user.expiry_date || "");
  };

  const handleExecuteAction = async () => {
    if (!targetUser || !activeModal) return;
    setIsSubmitting(true);
    try {
      let operation = "";
      if (activeModal === "lock") operation = "LOCK_ACCOUNT";
      else if (activeModal === "unlock") operation = "UNLOCK_ACCOUNT";
      else if (activeModal === "reset") operation = "RESET_PASSWORD";
      else if (activeModal === "expiry") operation = "SET_ACCOUNT_EXPIRY";
      else if (activeModal === "delete") operation = "DELETE_USER";

      await api.triggerUserAction(targetUser.id, {
        operation,
        new_password: newPassword || undefined,
        force_password_change: forcePasswordChange,
        expiry_date: expiryDate || undefined,
      });

      alert(`Operation '${operation}' successfully queued for ${targetUser.username} on ${targetUser.device_hostname}.`);
      setActiveModal(null);
      setTargetUser(null);
      fetchUsers();
      onRefreshDevices();
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            User Account Management
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            Inspect and manage Linux user credentials across all 10 workstations with safety safeguards
          </p>
        </div>

        <button onClick={fetchUsers} className="btn btn-secondary">
          <RefreshCw size={15} />
          <span>Refresh Users</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
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
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flex: 1, minWidth: "280px" }}>
          {/* Workstation Filter */}
          <div style={{ minWidth: "200px" }}>
            <label className="form-label">Filter by Workstation</label>
            <select
              className="form-select"
              value={selectedDeviceId || ""}
              onChange={(e) => setSelectedDeviceId(e.target.value ? Number(e.target.value) : undefined)}
            >
              <option value="">All Workstations ({devices.length})</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.hostname} ({d.ip_address})
                </option>
              ))}
            </select>
          </div>

          {/* Search Username */}
          <div style={{ flex: 1, maxWidth: "320px" }}>
            <label className="form-label">Search Username</label>
            <div style={{ position: "relative" }}>
              <Search
                size={16}
                style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }}
              />
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: "2.25rem" }}
                placeholder="e.g. student101"
                value={searchUsername}
                onChange={(e) => setSearchUsername(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div style={{ fontSize: "0.825rem", color: "var(--text-muted)" }}>
          {users.length} managed Linux accounts found
        </div>
      </div>

      {/* Users Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-medium)" }}>
              <th style={{ padding: "0.85rem 1rem" }}>Workstation</th>
              <th style={{ padding: "0.85rem 1rem" }}>Username</th>
              <th style={{ padding: "0.85rem 1rem" }}>Role Profile</th>
              <th style={{ padding: "0.85rem 1rem" }}>Account Status</th>
              <th style={{ padding: "0.85rem 1rem" }}>Expiration</th>
              <th style={{ padding: "0.85rem 1rem", textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                  <RefreshCw className="animate-spin" size={24} style={{ margin: "0 auto 0.5rem" }} />
                  <div>Loading workstation accounts...</div>
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                  <Users size={32} style={{ margin: "0 auto 0.5rem", opacity: 0.5 }} />
                  <div>No managed Linux accounts found matching filter.</div>
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "0.85rem 1rem", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                    {user.device_hostname}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {user.username}
                  </td>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    <span
                      style={{
                        padding: "0.2rem 0.5rem",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        background:
                          user.profile_name === "Administrator"
                            ? "rgba(239, 68, 68, 0.15)"
                            : user.profile_name === "Lab Assistant"
                            ? "rgba(245, 158, 11, 0.15)"
                            : "rgba(56, 189, 248, 0.15)",
                        color:
                          user.profile_name === "Administrator"
                            ? "var(--accent-rose)"
                            : user.profile_name === "Lab Assistant"
                            ? "var(--accent-amber)"
                            : "var(--accent-sky)",
                      }}
                    >
                      {user.profile_name}
                    </span>
                  </td>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    {user.is_locked ? (
                      <span className="badge badge-offline" style={{ textTransform: "none" }}>
                        <Lock size={12} />
                        <span>Locked</span>
                      </span>
                    ) : (
                      <span className="badge badge-online" style={{ textTransform: "none" }}>
                        <CheckCircle2 size={12} />
                        <span>Active</span>
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                    {user.expiry_date || "Never"}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: "0.4rem" }}>
                      {user.is_locked ? (
                        <button
                          onClick={() => handleOpenModal("unlock", user)}
                          className="btn btn-secondary"
                          style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", color: "#34d399" }}
                          title="Unlock account"
                        >
                          <Unlock size={14} />
                          <span>Unlock</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => handleOpenModal("lock", user)}
                          className="btn btn-secondary"
                          style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", color: "var(--accent-amber)" }}
                          title="Lock account login"
                        >
                          <Lock size={14} />
                          <span>Lock</span>
                        </button>
                      )}

                      <button
                        onClick={() => handleOpenModal("reset", user)}
                        className="btn btn-secondary"
                        style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
                        title="Reset password"
                      >
                        <Key size={14} />
                        <span>Reset PW</span>
                      </button>

                      <button
                        onClick={() => handleOpenModal("expiry", user)}
                        className="btn btn-secondary"
                        style={{ padding: "0.3rem", color: "var(--text-muted)" }}
                        title="Set account expiration date"
                      >
                        <Calendar size={14} />
                      </button>

                      <button
                        onClick={() => handleOpenModal("delete", user)}
                        className="btn btn-secondary"
                        style={{ padding: "0.3rem", color: "var(--accent-rose)" }}
                        title="Delete user account"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Action Modals */}
      {activeModal && targetUser && (
        <div className="modal-overlay" onClick={() => setActiveModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: "1.75rem" }}>
            {/* RESET PASSWORD MODAL */}
            {activeModal === "reset" && (
              <div>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                  Reset Password for '{targetUser.username}'
                </h3>
                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
                  Delivered via short-lived AES-256-GCM envelope and piped directly to chpasswd on workstation {targetUser.device_hostname}.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <div>
                    <label className="form-label">New Password (min 6 characters)</label>
                    <input
                      type="password"
                      className="form-input"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new strong password"
                    />
                  </div>

                  <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={forcePasswordChange}
                      onChange={(e) => setForcePasswordChange(e.target.checked)}
                    />
                    <span>Force user to change password at next login</span>
                  </label>
                </div>
              </div>
            )}

            {/* LOCK / UNLOCK CONFIRMATION */}
            {(activeModal === "lock" || activeModal === "unlock") && (
              <div>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                  {activeModal === "lock" ? "Lock Account" : "Unlock Account"}
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
                  Are you sure you want to {activeModal} account <strong>{targetUser.username}</strong> on workstation <strong>{targetUser.device_hostname}</strong>?
                </p>
                {activeModal === "lock" && (
                  <div style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.25)", padding: "0.75rem", borderRadius: "8px", fontSize: "0.8rem", color: "#fbbf24" }}>
                    Locking disables password login while keeping all student files and home directories intact.
                  </div>
                )}
              </div>
            )}

            {/* SET EXPIRY */}
            {activeModal === "expiry" && (
              <div>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                  Set Account Expiration Date
                </h3>
                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
                  Configure account expiration date (YYYY-MM-DD) for {targetUser.username} using Linux chage.
                </p>
                <div>
                  <label className="form-label">Expiration Date (YYYY-MM-DD)</label>
                  <input
                    type="date"
                    className="form-input"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                  />
                </div>
              </div>
            )}

            {/* DELETE USER CONFIRMATION */}
            {activeModal === "delete" && (
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--accent-rose)", marginBottom: "0.5rem" }}>
                  <AlertTriangle size={20} />
                  <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Confirm User Deletion</h3>
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
                  Are you sure you want to permanently delete account <strong>{targetUser.username}</strong> on workstation <strong>{targetUser.device_hostname}</strong>?
                </p>
                <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.25)", padding: "0.75rem", borderRadius: "8px", fontSize: "0.8rem", color: "#fca5a5" }}>
                  <strong>Warning:</strong> This will execute <code>userdel -r</code> locally, removing the student's home directory and mailbox. Existing system administrator accounts are protected and cannot be deleted.
                </div>
              </div>
            )}

            {/* Modal Buttons */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="btn btn-secondary"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteAction}
                className={activeModal === "delete" ? "btn btn-danger" : "btn btn-primary"}
                disabled={isSubmitting || (activeModal === "reset" && newPassword.length < 6)}
              >
                {isSubmitting ? "Dispatching..." : "Confirm Action"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
