"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Shield,
  Plus,
  Trash2,
  Terminal,
  FolderCheck,
  Users2,
  CheckCircle,
} from "lucide-react";
import { PermissionProfile, api } from "../lib/api";

interface ProfilesTabProps {
  profiles: PermissionProfile[];
  onRefreshProfiles: () => void;
}

export default function ProfilesTab({ profiles, onRefreshProfiles }: ProfilesTabProps) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [shell, setShell] = useState("/bin/bash");
  const [createHome, setCreateHome] = useState(true);
  const [primaryGroup, setPrimaryGroup] = useState("students");
  const [supplementaryGroups, setSupplementaryGroups] = useState("dialout,plugdev");
  const [sudoPolicy, setSudoPolicy] = useState<"none" | "restricted" | "admin">("none");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    try {
      await api.createProfile({
        name: name.trim(),
        description: description.trim(),
        shell,
        create_home: createHome,
        primary_group: primaryGroup.trim(),
        supplementary_groups: supplementaryGroups.trim(),
        sudo_policy: sudoPolicy,
      });
      setShowCreateModal(false);
      setName("");
      setDescription("");
      onRefreshProfiles();
    } catch (err: any) {
      alert(`Error creating profile: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteProfile = async (profile: PermissionProfile) => {
    if (profile.is_system) {
      alert("Built-in system profiles (Student, Lab Assistant, Administrator) cannot be deleted.");
      return;
    }
    if (!confirm(`Are you sure you want to delete profile '${profile.name}'?`)) return;
    try {
      await api.deleteProfile(profile.id);
      onRefreshProfiles();
    } catch (err: any) {
      alert(`Error deleting profile: ${err.message}`);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Permission Profiles & Policies
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            Role templates enforcing least privilege and Linux account access policies
          </p>
        </div>

        <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
          <Plus size={16} />
          <span>New Profile</span>
        </button>
      </div>

      {/* Profile Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "1.25rem",
        }}
      >
        {profiles.map((p) => {
          const isSystem = p.is_system;
          const isStudent = p.name === "Student";
          const isLabAsst = p.name === "Lab Assistant";
          const isAdmin = p.name === "Administrator";

          return (
            <div
              key={p.id}
              className="card"
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "1.25rem",
                position: "relative",
              }}
            >
              <div>
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <div
                      style={{
                        padding: "0.6rem",
                        borderRadius: "10px",
                        background: isAdmin
                          ? "rgba(239, 68, 68, 0.15)"
                          : isLabAsst
                          ? "rgba(245, 158, 11, 0.15)"
                          : "rgba(56, 189, 248, 0.15)",
                        color: isAdmin
                          ? "var(--accent-rose)"
                          : isLabAsst
                          ? "var(--accent-amber)"
                          : "var(--accent-sky)",
                      }}
                    >
                      {isAdmin ? <ShieldAlert size={22} /> : isLabAsst ? <ShieldCheck size={22} /> : <Shield size={22} />}
                    </div>
                    <div>
                      <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>{p.name}</h3>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        {isSystem ? "Built-in System Profile" : "Custom Profile"}
                      </span>
                    </div>
                  </div>

                  {!isSystem && (
                    <button
                      onClick={() => handleDeleteProfile(p)}
                      className="btn btn-secondary"
                      style={{ padding: "0.35rem", color: "var(--accent-rose)" }}
                      title="Delete profile"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>

                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
                  {p.description}
                </p>

                {/* Policy Specs */}
                <div
                  style={{
                    background: "var(--bg-secondary)",
                    borderRadius: "8px",
                    padding: "0.85rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.5rem",
                    fontSize: "0.8rem",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      <Terminal size={14} />
                      Login Shell:
                    </span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{p.shell}</span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      <FolderCheck size={14} />
                      Home Directory:
                    </span>
                    <span style={{ fontWeight: 500 }}>{p.create_home ? "Created (/home)" : "None"}</span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      <Users2 size={14} />
                      Primary Group:
                    </span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{p.primary_group}</span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ color: "var(--text-muted)" }}>Extra Groups:</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      {p.supplementary_groups || "None"}
                    </span>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      borderTop: "1px solid var(--border-subtle)",
                      paddingTop: "0.4rem",
                      marginTop: "0.2rem",
                    }}
                  >
                    <span style={{ color: "var(--text-muted)" }}>Sudo Privilege:</span>
                    <span
                      style={{
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        padding: "0.15rem 0.45rem",
                        borderRadius: "4px",
                        background:
                          p.sudo_policy === "none"
                            ? "rgba(16, 185, 129, 0.15)"
                            : p.sudo_policy === "restricted"
                            ? "rgba(245, 158, 11, 0.15)"
                            : "rgba(239, 68, 68, 0.15)",
                        color:
                          p.sudo_policy === "none"
                            ? "#34d399"
                            : p.sudo_policy === "restricted"
                            ? "var(--accent-amber)"
                            : "var(--accent-rose)",
                      }}
                    >
                      {p.sudo_policy === "none"
                        ? "NO SUDO"
                        : p.sudo_policy === "restricted"
                        ? "RESTRICTED POLICY"
                        : "ADMIN"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Security Safeguard Note */}
              <div
                style={{
                  fontSize: "0.72rem",
                  color: "var(--text-muted)",
                  borderTop: "1px solid var(--border-subtle)",
                  paddingTop: "0.6rem",
                }}
              >
                {isStudent && "Enforces standard user privileges. Sudo execution is forbidden."}
                {isLabAsst && "Scoped support privileges. No root escalation unless explicitly granted."}
                {isAdmin && "Strictly restricted administrative profile. Arbitrary sudoers editing is disabled."}
              </div>
            </div>
          );
        })}
      </div>

      {/* Create Profile Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: "1.75rem" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Create Custom Permission Profile
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Define a new Linux account role template with predefined groups, shell, and sudo rules.
            </p>

            <form onSubmit={handleCreateProfile} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label className="form-label">Profile Name</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. Robotics Student"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label className="form-label">Description</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Access to serial port and robot controllers"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label className="form-label">Login Shell</label>
                  <input
                    type="text"
                    className="form-input"
                    value={shell}
                    onChange={(e) => setShell(e.target.value)}
                  />
                </div>

                <div>
                  <label className="form-label">Primary Group</label>
                  <input
                    type="text"
                    className="form-input"
                    value={primaryGroup}
                    onChange={(e) => setPrimaryGroup(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="form-label">Supplementary Groups (comma separated)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. dialout,plugdev,wireshark"
                  value={supplementaryGroups}
                  onChange={(e) => setSupplementaryGroups(e.target.value)}
                />
              </div>

              <div>
                <label className="form-label">Sudo Policy</label>
                <select
                  className="form-select"
                  value={sudoPolicy}
                  onChange={(e) => setSudoPolicy(e.target.value as any)}
                >
                  <option value="none">None (Standard user without sudo)</option>
                  <option value="restricted">Restricted (Scoped commands policy)</option>
                  <option value="admin">Administrator (Restricted administrative)</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn btn-secondary"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? "Creating..." : "Save Profile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
