"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  RotateCcw,
  XCircle,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Terminal,
} from "lucide-react";
import { ProvisioningTask, Device, api } from "../lib/api";

interface TaskProgressTabProps {
  devices: Device[];
  onRefreshDevices: () => void;
}

export default function TaskProgressTab({ devices, onRefreshDevices }: TaskProgressTabProps) {
  const [tasks, setTasks] = useState<ProvisioningTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | undefined>(undefined);
  const [selectedTask, setSelectedTask] = useState<ProvisioningTask | null>(null);

  const fetchTasks = async () => {
    setIsLoading(true);
    try {
      const data = await api.getTasks(statusFilter || undefined, selectedDeviceId);
      setTasks(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 4000);
    return () => clearInterval(interval);
  }, [statusFilter, selectedDeviceId]);

  const handleRetry = async (taskId: string) => {
    try {
      await api.retryTask(taskId);
      fetchTasks();
      onRefreshDevices();
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    }
  };

  const handleCancel = async (taskId: string) => {
    if (!confirm("Are you sure you want to cancel this queued task?")) return;
    try {
      await api.cancelTask(taskId);
      fetchTasks();
      onRefreshDevices();
    } catch (err: any) {
      alert(`Cancel failed: ${err.message}`);
    }
  };

  const formatTimestamp = (iso?: string) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Task Progress & Execution Queue
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            Real-time status of account provisioning and maintenance tasks across all workstations
          </p>
        </div>

        <button onClick={fetchTasks} className="btn btn-secondary">
          <RefreshCw size={15} />
          <span>Refresh Tasks</span>
        </button>
      </div>

      {/* Filter Bar */}
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
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <div>
            <label className="form-label">Status Filter</label>
            <select
              className="form-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ minWidth: "160px" }}
            >
              <option value="">All Statuses</option>
              <option value="QUEUED">Queued</option>
              <option value="RUNNING">Running</option>
              <option value="SUCCEEDED">Succeeded</option>
              <option value="FAILED">Failed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>

          <div>
            <label className="form-label">Filter by Workstation</label>
            <select
              className="form-select"
              value={selectedDeviceId || ""}
              onChange={(e) => setSelectedDeviceId(e.target.value ? Number(e.target.value) : undefined)}
              style={{ minWidth: "180px" }}
            >
              <option value="">All Workstations</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.hostname}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ fontSize: "0.825rem", color: "var(--text-muted)" }}>
          {tasks.length} total tasks recorded
        </div>
      </div>

      {/* Tasks Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-medium)" }}>
              <th style={{ padding: "0.85rem 1rem" }}>Workstation</th>
              <th style={{ padding: "0.85rem 1rem" }}>Operation</th>
              <th style={{ padding: "0.85rem 1rem" }}>Target User</th>
              <th style={{ padding: "0.85rem 1rem" }}>Status</th>
              <th style={{ padding: "0.85rem 1rem" }}>Queued At</th>
              <th style={{ padding: "0.85rem 1rem" }}>Completed</th>
              <th style={{ padding: "0.85rem 1rem", textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && tasks.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                  <RefreshCw className="animate-spin" size={24} style={{ margin: "0 auto 0.5rem" }} />
                  <div>Loading tasks...</div>
                </td>
              </tr>
            ) : tasks.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                  <Activity size={32} style={{ margin: "0 auto 0.5rem", opacity: 0.5 }} />
                  <div>No provisioning tasks found matching filters.</div>
                </td>
              </tr>
            ) : (
              tasks.map((task) => (
                <tr key={task.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "0.85rem 1rem", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                    {task.device_hostname}
                  </td>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    <code style={{ fontFamily: "var(--font-mono)", color: "var(--accent-sky)", fontSize: "0.8rem" }}>
                      {task.operation}
                    </code>
                  </td>
                  <td style={{ padding: "0.85rem 1rem", fontWeight: 600 }}>
                    {task.target_username}
                  </td>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    <span className={`badge badge-${task.status.toLowerCase()}`}>
                      {task.status}
                    </span>
                    {task.error_message && (
                      <div
                        style={{
                          fontSize: "0.72rem",
                          color: "var(--accent-rose)",
                          marginTop: "0.25rem",
                          maxWidth: "240px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={task.error_message}
                      >
                        {task.error_message}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                    {formatTimestamp(task.queued_at)}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                    {formatTimestamp(task.completed_at)}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: "0.4rem" }}>
                      {task.status === "FAILED" && (
                        <button
                          onClick={() => handleRetry(task.id)}
                          className="btn btn-secondary"
                          style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", color: "var(--accent-sky)" }}
                          title="Retry failed task"
                        >
                          <RotateCcw size={13} />
                          <span>Retry</span>
                        </button>
                      )}

                      {task.status === "QUEUED" && (
                        <button
                          onClick={() => handleCancel(task.id)}
                          className="btn btn-secondary"
                          style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", color: "var(--accent-rose)" }}
                          title="Cancel queued task"
                        >
                          <XCircle size={13} />
                          <span>Cancel</span>
                        </button>
                      )}

                      <button
                        onClick={() => setSelectedTask(task)}
                        className="btn btn-secondary"
                        style={{ padding: "0.3rem 0.5rem", fontSize: "0.75rem" }}
                        title="View Execution Details"
                      >
                        Details
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <div className="modal-overlay" onClick={() => setSelectedTask(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: "1.75rem" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Task Details
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Workstation execution diagnostic logs
            </p>

            <div style={{ background: "var(--bg-secondary)", borderRadius: "8px", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.825rem", marginBottom: "1.25rem" }}>
              <div><strong>Task ID:</strong> <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{selectedTask.id}</span></div>
              <div><strong>Workstation:</strong> {selectedTask.device_hostname}</div>
              <div><strong>Operation:</strong> <code>{selectedTask.operation}</code></div>
              <div><strong>Target Username:</strong> {selectedTask.target_username}</div>
              <div><strong>Status:</strong> <span className={`badge badge-${selectedTask.status.toLowerCase()}`}>{selectedTask.status}</span></div>
              <div><strong>Attempts:</strong> {selectedTask.attempts} / {selectedTask.max_attempts}</div>

              {selectedTask.error_message && (
                <div style={{ color: "var(--accent-rose)", marginTop: "0.5rem" }}>
                  <strong>Error Message:</strong>
                  <pre style={{ background: "rgba(239, 68, 68, 0.1)", padding: "0.5rem", borderRadius: "4px", marginTop: "0.25rem", whiteSpace: "pre-wrap" }}>
                    {selectedTask.error_message}
                  </pre>
                </div>
              )}

              {selectedTask.result_details_json && (
                <div style={{ marginTop: "0.5rem" }}>
                  <strong>Execution Output:</strong>
                  <pre style={{ background: "rgba(0, 0, 0, 0.4)", padding: "0.5rem", borderRadius: "4px", marginTop: "0.25rem", fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                    {selectedTask.result_details_json}
                  </pre>
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              {selectedTask.status === "FAILED" && (
                <button
                  onClick={() => {
                    handleRetry(selectedTask.id);
                    setSelectedTask(null);
                  }}
                  className="btn btn-primary"
                >
                  <RotateCcw size={14} />
                  <span>Retry Task Now</span>
                </button>
              )}
              <button onClick={() => setSelectedTask(null)} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
