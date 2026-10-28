"use client";

import React, { useState, useEffect } from "react";
import {
  UserPlus,
  Upload,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Download,
  Eye,
  EyeOff,
  RefreshCw,
  Wand2,
  Shield,
  ArrowRight,
  RotateCcw,
  XCircle,
  Check,
} from "lucide-react";
import {
  Device,
  PermissionProfile,
  ProvisioningBatch,
  CSVValidateResponse,
  api,
} from "../lib/api";

interface BulkProvisioningTabProps {
  devices: Device[];
  profiles: PermissionProfile[];
  initialSelectedHost?: string;
  onRefreshDevices: () => void;
}

interface FormRow {
  selected: boolean;
  hostname: string;
  username: string;
  initialPassword: string;
  role: string;
  forcePasswordChange: boolean;
  isPasswordVisible: boolean;
  error?: string;
}

export default function BulkProvisioningTab({
  devices,
  profiles,
  initialSelectedHost,
  onRefreshDevices,
}: BulkProvisioningTabProps) {
  const [mode, setMode] = useState<"form" | "csv">("form");
  const [formRows, setFormRows] = useState<FormRow[]>([]);
  const [batchName, setBatchName] = useState("");
  
  // Preview Modal
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Active Batch Monitoring
  const [activeBatch, setActiveBatch] = useState<ProvisioningBatch | null>(null);

  // CSV States
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvValidation, setCsvValidation] = useState<CSVValidateResponse | null>(null);
  const [isValidatingCsv, setIsValidatingCsv] = useState(false);

  // Populate form rows based on available devices
  useEffect(() => {
    // Standard default usernames from prompt example
    const defaultExamples: { [key: string]: { user: string; role: string } } = {
      "LAB-PC-01": { user: "student101", role: "Student" },
      "LAB-PC-02": { user: "student102", role: "Student" },
      "LAB-PC-03": { user: "student103", role: "Student" },
      "LAB-PC-04": { user: "student104", role: "Student" },
      "LAB-PC-05": { user: "student105", role: "Student" },
      "LAB-PC-06": { user: "student106", role: "Student" },
      "LAB-PC-07": { user: "student107", role: "Student" },
      "LAB-PC-08": { user: "student108", role: "Student" },
      "LAB-PC-09": { user: "student109", role: "Student" },
      "LAB-PC-10": { user: "labassistant1", role: "Lab Assistant" },
    };

    const rows: FormRow[] = devices.map((dev, idx) => {
      const isSelected = initialSelectedHost ? dev.hostname === initialSelectedHost : true;
      const example = defaultExamples[dev.hostname] || {
        user: `student${100 + idx + 1}`,
        role: "Student",
      };

      return {
        selected: isSelected,
        hostname: dev.hostname,
        username: example.user,
        initialPassword: generateSecurePassword(),
        role: example.role,
        forcePasswordChange: true,
        isPasswordVisible: false,
      };
    });

    setFormRows(rows);
    setBatchName(`LabBatch-${new Date().toISOString().slice(0, 10)}`);
  }, [devices, initialSelectedHost]);

  // Periodic poll of active batch progress
  useEffect(() => {
    if (!activeBatch || activeBatch.status === "COMPLETED" || activeBatch.status === "FAILED") {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const updated = await api.getBatch(activeBatch.id);
        setActiveBatch(updated);
        onRefreshDevices();
      } catch (err) {
        // ignore
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [activeBatch, onRefreshDevices]);

  function generateSecurePassword() {
    const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%";
    let pass = "";
    for (let i = 0; i < 12; i++) {
      pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return pass;
  }

  const handleSelectAll = (select: boolean) => {
    setFormRows((prev) => prev.map((r) => ({ ...r, selected: select })));
  };

  const handleGenerateAllPasswords = () => {
    setFormRows((prev) =>
      prev.map((r) => ({
        ...r,
        initialPassword: generateSecurePassword(),
      }))
    );
  };

  const handleRowChange = (index: number, field: keyof FormRow, value: any) => {
    setFormRows((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const validateFormRows = (): boolean => {
    const selectedRows = formRows.filter((r) => r.selected);
    if (selectedRows.length === 0) {
      alert("Please select at least one workstation for user provisioning.");
      return false;
    }

    const usernameRegex = /^[a-z_][a-z0-9_-]{0,31}$/;
    const protectedAccounts = [
      "root", "ubuntu", "admin", "administrator", "sudo", "sys", "daemon",
      "bin", "sync", "games", "nobody", "sshd"
    ];

    let hasErrors = false;
    const updated = formRows.map((r) => {
      if (!r.selected) return { ...r, error: undefined };
      const u = r.username.trim().toLowerCase();
      if (!u) {
        hasErrors = true;
        return { ...r, error: "Username cannot be empty" };
      }
      if (!usernameRegex.test(u)) {
        hasErrors = true;
        return { ...r, error: "Invalid POSIX username (lowercase, start with letter)" };
      }
      if (protectedAccounts.includes(u)) {
        hasErrors = true;
        return { ...r, error: `Account '${u}' is protected` };
      }
      if (r.initialPassword.length < 6) {
        hasErrors = true;
        return { ...r, error: "Password must be >= 6 characters" };
      }
      return { ...r, error: undefined };
    });

    setFormRows(updated);
    return !hasErrors;
  };

  const handleOpenPreview = () => {
    if (validateFormRows()) {
      setShowPreviewModal(true);
    }
  };

  const handleConfirmProvisioning = async () => {
    setIsSubmitting(true);
    const selectedRows = formRows.filter((r) => r.selected);
    try {
      const items = selectedRows.map((r) => ({
        hostname: r.hostname,
        username: r.username.trim().toLowerCase(),
        initial_password: r.initialPassword,
        role: r.role,
        force_password_change: r.forcePasswordChange,
      }));

      const batch = await api.bulkProvision(batchName, items);
      setActiveBatch(batch);
      setShowPreviewModal(false);
      onRefreshDevices();
    } catch (err: any) {
      alert(`Provisioning failed to start: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // CSV Upload & Validation
  const handleCsvFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFile(file);
    setIsValidatingCsv(true);
    try {
      const res = await api.validateCsv(file);
      setCsvValidation(res);
    } catch (err: any) {
      alert(`CSV Validation failed: ${err.message}`);
      setCsvValidation(null);
    } finally {
      setIsValidatingCsv(false);
    }
  };

  const handleConfirmCsvProvisioning = async () => {
    if (!csvValidation || !csvValidation.is_valid) return;
    setIsSubmitting(true);
    try {
      // Execute CSV entries
      const items = csvValidation.rows.map((r) => ({
        hostname: r.hostname,
        username: r.username.trim().toLowerCase(),
        initial_password: r.initial_password === "[MASKED]" ? "InitialStudentPass2026!" : r.initial_password,
        role: r.role,
        force_password_change: r.force_password_change,
      }));

      const batch = await api.bulkProvision(batchName || "CSV-Batch", items);
      setActiveBatch(batch);
      setCsvFile(null);
      setCsvValidation(null);
      onRefreshDevices();
    } catch (err: any) {
      alert(`CSV provisioning submission failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownloadSampleCsv = () => {
    const content =
      "hostname,username,initial_password,role,force_password_change\n" +
      "LAB-PC-01,student101,PassLab101!#,Student,true\n" +
      "LAB-PC-02,student102,PassLab102!#,Student,true\n" +
      "LAB-PC-03,student103,PassLab103!#,Student,true\n" +
      "LAB-PC-04,student104,PassLab104!#,Student,true\n" +
      "LAB-PC-05,student105,PassLab105!#,Student,true\n" +
      "LAB-PC-06,student106,PassLab106!#,Student,true\n" +
      "LAB-PC-07,student107,PassLab107!#,Student,true\n" +
      "LAB-PC-08,student108,PassLab108!#,Student,true\n" +
      "LAB-PC-09,student109,PassLab109!#,Student,true\n" +
      "LAB-PC-10,labassistant1,PassLabAsst!#,Lab Assistant,false\n";

    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "ubuntu_lab_sample.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleRetryTask = async (taskId: string) => {
    try {
      await api.retryTask(taskId);
      if (activeBatch) {
        const updated = await api.getBatch(activeBatch.id);
        setActiveBatch(updated);
      }
    } catch (err: any) {
      alert(`Retry error: ${err.message}`);
    }
  };

  const selectedCount = formRows.filter((r) => r.selected).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Title & Mode Switcher */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Bulk User Provisioning
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            Provision individualized student accounts across multiple Ubuntu workstations in a single submission
          </p>
        </div>

        {/* Tab switch */}
        <div style={{ display: "flex", background: "var(--bg-secondary)", padding: "0.25rem", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
          <button
            onClick={() => setMode("form")}
            className="btn btn-secondary"
            style={{
              fontSize: "0.825rem",
              padding: "0.4rem 0.9rem",
              border: "none",
              background: mode === "form" ? "var(--bg-surface)" : "transparent",
              color: mode === "form" ? "var(--text-primary)" : "var(--text-muted)",
              fontWeight: mode === "form" ? 600 : 500,
            }}
          >
            <UserPlus size={15} />
            <span>Interactive Form</span>
          </button>
          <button
            onClick={() => setMode("csv")}
            className="btn btn-secondary"
            style={{
              fontSize: "0.825rem",
              padding: "0.4rem 0.9rem",
              border: "none",
              background: mode === "csv" ? "var(--bg-surface)" : "transparent",
              color: mode === "csv" ? "var(--text-primary)" : "var(--text-muted)",
              fontWeight: mode === "csv" ? 600 : 500,
            }}
          >
            <FileSpreadsheet size={15} />
            <span>CSV Import</span>
          </button>
        </div>
      </div>

      {/* Active Batch Progress Monitor if running */}
      {activeBatch && (
        <div
          className="card"
          style={{
            borderColor:
              activeBatch.status === "COMPLETED"
                ? "rgba(16, 185, 129, 0.4)"
                : activeBatch.status === "FAILED"
                ? "rgba(239, 68, 68, 0.4)"
                : "rgba(56, 189, 248, 0.4)",
            background: "rgba(17, 28, 53, 0.9)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontWeight: 700, fontSize: "1.1rem" }}>{activeBatch.name}</span>
                <span className={`badge badge-${activeBatch.status.toLowerCase()}`}>
                  {activeBatch.status}
                </span>
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
                Batch ID: {activeBatch.id} • {activeBatch.succeeded_tasks} of {activeBatch.total_tasks} workstations complete
              </div>
            </div>

            <button
              onClick={async () => {
                const updated = await api.getBatch(activeBatch.id);
                setActiveBatch(updated);
              }}
              className="btn btn-secondary"
              style={{ fontSize: "0.75rem" }}
            >
              <RefreshCw size={13} />
              <span>Refresh Batch</span>
            </button>
          </div>

          {/* Progress Bar */}
          <div style={{ width: "100%", height: "8px", background: "var(--bg-secondary)", borderRadius: "4px", overflow: "hidden", marginBottom: "1.25rem" }}>
            <div
              style={{
                height: "100%",
                width: `${(activeBatch.succeeded_tasks / (activeBatch.total_tasks || 1)) * 100}%`,
                background: "linear-gradient(90deg, #0284c7 0%, #10b981 100%)",
                transition: "width 0.4s ease",
              }}
            />
          </div>

          {/* Tasks List */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.75rem" }}>
            {activeBatch.tasks.map((task) => (
              <div
                key={task.id}
                style={{
                  background: "var(--bg-secondary)",
                  padding: "0.75rem",
                  borderRadius: "8px",
                  border: "1px solid var(--border-subtle)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", fontFamily: "var(--font-mono)" }}>
                    {task.device_hostname}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    User: <span style={{ color: "var(--text-primary)" }}>{task.target_username}</span>
                  </div>
                  {task.error_message && (
                    <div style={{ fontSize: "0.7rem", color: "var(--accent-rose)", marginTop: "0.2rem" }}>
                      {task.error_message}
                    </div>
                  )}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span className={`badge badge-${task.status.toLowerCase()}`} style={{ fontSize: "0.68rem" }}>
                    {task.status}
                  </span>
                  {task.status === "FAILED" && (
                    <button
                      onClick={() => handleRetryTask(task.id)}
                      className="btn btn-secondary"
                      style={{ padding: "0.25rem 0.4rem", fontSize: "0.7rem" }}
                      title="Retry task on this PC"
                    >
                      <RotateCcw size={12} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* FORM MODE */}
      {mode === "form" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Controls Bar */}
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
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <div>
                <label className="form-label">Batch Label</label>
                <input
                  type="text"
                  className="form-input"
                  style={{ width: "240px" }}
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", alignItems: "flex-end", height: "100%", paddingTop: "1.25rem", gap: "0.5rem" }}>
                <button
                  type="button"
                  onClick={() => handleSelectAll(true)}
                  className="btn btn-secondary"
                  style={{ fontSize: "0.75rem" }}
                >
                  Select All ({devices.length})
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectAll(false)}
                  className="btn btn-secondary"
                  style={{ fontSize: "0.75rem" }}
                >
                  Deselect All
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
              <button
                type="button"
                onClick={handleGenerateAllPasswords}
                className="btn btn-secondary"
                style={{ fontSize: "0.8rem" }}
                title="Generate distinct random passwords for all selected workstations"
              >
                <Wand2 size={14} />
                <span>Generate Passwords</span>
              </button>

              <button
                type="button"
                onClick={handleOpenPreview}
                className="btn btn-primary"
                disabled={selectedCount === 0}
              >
                <span>Validate & Preview ({selectedCount} PCs)</span>
                <ArrowRight size={15} />
              </button>
            </div>
          </div>

          {/* Table of 10 PCs */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-medium)" }}>
                  <th style={{ padding: "0.85rem 1rem", width: "40px" }}></th>
                  <th style={{ padding: "0.85rem 1rem" }}>Workstation</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Username</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Initial Password</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Permission Profile</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Force PW Change</th>
                </tr>
              </thead>
              <tbody>
                {formRows.map((row, idx) => {
                  const dev = devices.find((d) => d.hostname === row.hostname);
                  const isOnline = dev?.status === "online";

                  return (
                    <tr
                      key={row.hostname}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        background: row.selected ? "transparent" : "rgba(0, 0, 0, 0.2)",
                        opacity: row.selected ? 1 : 0.6,
                      }}
                    >
                      {/* Checkbox */}
                      <td style={{ padding: "0.75rem 1rem" }}>
                        <input
                          type="checkbox"
                          checked={row.selected}
                          onChange={(e) => handleRowChange(idx, "selected", e.target.checked)}
                          style={{ cursor: "pointer", width: "16px", height: "16px" }}
                        />
                      </td>

                      {/* Workstation */}
                      <td style={{ padding: "0.75rem 1rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span style={{ fontWeight: 600, fontFamily: "var(--font-mono)" }}>
                            {row.hostname}
                          </span>
                          <span className={`status-dot status-dot-${isOnline ? "online" : "offline"}`} />
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {dev?.ip_address || "LAN DHCP"}
                        </div>
                      </td>

                      {/* Username */}
                      <td style={{ padding: "0.75rem 1rem" }}>
                        <input
                          type="text"
                          className="form-input"
                          value={row.username}
                          onChange={(e) => handleRowChange(idx, "username", e.target.value)}
                          disabled={!row.selected}
                          placeholder="e.g. student101"
                          style={{
                            maxWidth: "180px",
                            borderColor: row.error ? "var(--accent-rose)" : undefined,
                          }}
                        />
                        {row.error && (
                          <div style={{ fontSize: "0.7rem", color: "var(--accent-rose)", marginTop: "0.25rem" }}>
                            {row.error}
                          </div>
                        )}
                      </td>

                      {/* Initial Password */}
                      <td style={{ padding: "0.75rem 1rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                          <input
                            type={row.isPasswordVisible ? "text" : "password"}
                            className="form-input"
                            value={row.initialPassword}
                            onChange={(e) => handleRowChange(idx, "initialPassword", e.target.value)}
                            disabled={!row.selected}
                            style={{ maxWidth: "160px", fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}
                          />
                          <button
                            type="button"
                            onClick={() => handleRowChange(idx, "isPasswordVisible", !row.isPasswordVisible)}
                            className="btn btn-secondary"
                            style={{ padding: "0.35rem", color: "var(--text-muted)" }}
                            title={row.isPasswordVisible ? "Hide Password" : "Show Password"}
                          >
                            {row.isPasswordVisible ? <EyeOff size={14} /> : <Eye size={14} />}
                          </button>
                        </div>
                      </td>

                      {/* Profile */}
                      <td style={{ padding: "0.75rem 1rem" }}>
                        <select
                          className="form-select"
                          value={row.role}
                          onChange={(e) => handleRowChange(idx, "role", e.target.value)}
                          disabled={!row.selected}
                          style={{ maxWidth: "170px" }}
                        >
                          {profiles.map((p) => (
                            <option key={p.id} value={p.name}>
                              {p.name}
                            </option>
                          ))}
                        </select>
                      </td>

                      {/* Force Password Change */}
                      <td style={{ padding: "0.75rem 1rem" }}>
                        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", fontSize: "0.8rem" }}>
                          <input
                            type="checkbox"
                            checked={row.forcePasswordChange}
                            onChange={(e) => handleRowChange(idx, "forcePasswordChange", e.target.checked)}
                            disabled={!row.selected}
                          />
                          <span>Expire at 1st Login</span>
                        </label>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CSV IMPORT MODE */}
      {mode === "csv" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* File Upload Box */}
          <div
            className="card"
            style={{
              padding: "2.5rem 1.5rem",
              textAlign: "center",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "1rem",
              border: "2px dashed var(--border-medium)",
              background: "rgba(17, 28, 53, 0.4)",
            }}
          >
            <Upload size={36} style={{ color: "var(--accent-sky)" }} />
            <div>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Import Accounts from CSV File</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.825rem", marginTop: "0.25rem" }}>
                Columns required: <code style={{ fontFamily: "var(--font-mono)", color: "var(--accent-sky)" }}>hostname,username,initial_password,role,force_password_change</code>
              </p>
            </div>

            <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
              <label className="btn btn-primary" style={{ cursor: "pointer" }}>
                <span>{csvFile ? `Selected: ${csvFile.name}` : "Choose CSV File"}</span>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleCsvFileChange}
                  style={{ display: "none" }}
                />
              </label>

              <button onClick={handleDownloadSampleCsv} className="btn btn-secondary">
                <Download size={15} />
                <span>Download Sample CSV</span>
              </button>
            </div>
          </div>

          {/* Validation Feedback */}
          {isValidatingCsv && (
            <div className="card" style={{ textAlign: "center", padding: "1.5rem" }}>
              <RefreshCw className="animate-spin" size={24} style={{ margin: "0 auto", color: "var(--accent-sky)" }} />
              <p style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                Validating CSV rows against registered PCs and security policies...
              </p>
            </div>
          )}

          {csvValidation && (
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {csvValidation.is_valid ? (
                    <CheckCircle2 size={20} style={{ color: "var(--accent-emerald)" }} />
                  ) : (
                    <AlertCircle size={20} style={{ color: "var(--accent-rose)" }} />
                  )}
                  <span style={{ fontWeight: 600, fontSize: "1rem" }}>
                    {csvValidation.is_valid
                      ? `All ${csvValidation.total_rows} rows valid and ready for provisioning`
                      : `Found errors in ${csvValidation.invalid_rows} of ${csvValidation.total_rows} rows`}
                  </span>
                </div>

                <button
                  onClick={handleConfirmCsvProvisioning}
                  className="btn btn-primary"
                  disabled={!csvValidation.is_valid || isSubmitting}
                >
                  {isSubmitting ? "Provisioning..." : `Execute Provisioning (${csvValidation.valid_rows} Users)`}
                </button>
              </div>

              {/* Rows Diagnostic Table */}
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.825rem" }}>
                  <thead>
                    <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-medium)" }}>
                      <th style={{ padding: "0.6rem 0.8rem", width: "60px" }}>Row</th>
                      <th style={{ padding: "0.6rem 0.8rem" }}>Workstation</th>
                      <th style={{ padding: "0.6rem 0.8rem" }}>Username</th>
                      <th style={{ padding: "0.6rem 0.8rem" }}>Password</th>
                      <th style={{ padding: "0.6rem 0.8rem" }}>Role</th>
                      <th style={{ padding: "0.6rem 0.8rem" }}>Diagnostics</th>
                    </tr>
                  </thead>
                  <tbody>
                    {csvValidation.rows.map((row) => (
                      <tr
                        key={row.row_number}
                        style={{
                          borderBottom: "1px solid var(--border-subtle)",
                          background: row.is_valid ? "transparent" : "rgba(239, 68, 68, 0.08)",
                        }}
                      >
                        <td style={{ padding: "0.6rem 0.8rem", color: "var(--text-muted)" }}>
                          #{row.row_number}
                        </td>
                        <td style={{ padding: "0.6rem 0.8rem", fontFamily: "var(--font-mono)" }}>
                          {row.hostname}
                        </td>
                        <td style={{ padding: "0.6rem 0.8rem", fontFamily: "var(--font-mono)" }}>
                          {row.username}
                        </td>
                        <td style={{ padding: "0.6rem 0.8rem", color: "var(--text-muted)" }}>
                          {row.initial_password}
                        </td>
                        <td style={{ padding: "0.6rem 0.8rem" }}>{row.role}</td>
                        <td style={{ padding: "0.6rem 0.8rem" }}>
                          {row.is_valid ? (
                            <span style={{ color: "#34d399", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                              <Check size={14} />
                              <span>Valid</span>
                            </span>
                          ) : (
                            <div style={{ color: "var(--accent-rose)", display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                              {row.errors.map((err, i) => (
                                <span key={i}>• {err}</span>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confirmation & Preview Modal */}
      {showPreviewModal && (
        <div className="modal-overlay" onClick={() => setShowPreviewModal(false)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "680px", padding: "1.75rem" }}
          >
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Preview Bulk User Provisioning
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Review account assignments before tasks are cryptographically queued and dispatched to client workstations.
            </p>

            <div
              style={{
                background: "var(--bg-secondary)",
                borderRadius: "8px",
                padding: "0.75rem",
                maxHeight: "260px",
                overflowY: "auto",
                marginBottom: "1.25rem",
              }}
            >
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-medium)", color: "var(--text-muted)" }}>
                    <th style={{ padding: "0.5rem", textAlign: "left" }}>Workstation</th>
                    <th style={{ padding: "0.5rem", textAlign: "left" }}>Username</th>
                    <th style={{ padding: "0.5rem", textAlign: "left" }}>Role</th>
                    <th style={{ padding: "0.5rem", textAlign: "left" }}>Initial Password</th>
                  </tr>
                </thead>
                <tbody>
                  {formRows
                    .filter((r) => r.selected)
                    .map((r) => (
                      <tr key={r.hostname} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)" }}>{r.hostname}</td>
                        <td style={{ padding: "0.5rem", fontWeight: 600 }}>{r.username}</td>
                        <td style={{ padding: "0.5rem" }}>{r.role}</td>
                        <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", color: "var(--accent-sky)" }}>
                          ••••••••••••
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            <div
              style={{
                background: "rgba(56, 189, 248, 0.08)",
                border: "1px solid rgba(56, 189, 248, 0.2)",
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                fontSize: "0.78rem",
                color: "var(--text-secondary)",
                marginBottom: "1.5rem",
              }}
            >
              <strong>Offline PC Resilience:</strong> If any workstation is currently offline, its task will safely remain in the database queue and execute automatically as soon as the agent connects, without delaying other workstations.
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                type="button"
                onClick={() => setShowPreviewModal(false)}
                className="btn btn-secondary"
                disabled={isSubmitting}
              >
                Back to Edit
              </button>
              <button
                type="button"
                onClick={handleConfirmProvisioning}
                className="btn btn-primary"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Dispatching..." : `Confirm & Provision (${selectedCount} Accounts)`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
