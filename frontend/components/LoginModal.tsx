"use client";

import React, { useState } from "react";
import { Server, Lock, User, ArrowRight, Shield } from "lucide-react";
import { api, setAuthToken, AdminUser } from "../lib/api";

interface LoginModalProps {
  onLoginSuccess: (admin: AdminUser) => void;
}

export default function LoginModal({ onLoginSuccess }: LoginModalProps) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await api.login(username.trim(), password);
      setAuthToken(res.access_token);
      onLoginSuccess(res.admin_user);
    } catch (err: any) {
      setError(err.message || "Invalid administrator credentials");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" style={{ backdropFilter: "blur(16px)" }}>
      <div
        className="modal-content"
        style={{
          maxWidth: "440px",
          padding: "2.25rem",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-medium)",
          boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 30px rgba(2, 132, 199, 0.15)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "1.75rem" }}>
          <div
            style={{
              width: "52px",
              height: "52px",
              borderRadius: "14px",
              background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 1rem",
              boxShadow: "0 4px 20px rgba(2, 132, 199, 0.5)",
            }}
          >
            <Server size={28} />
          </div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Ubuntu Lab Manager
          </h2>
          <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
            Sign in to access workstation administration
          </p>
        </div>

        {error && (
          <div
            style={{
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#fca5a5",
              borderRadius: "8px",
              padding: "0.75rem",
              fontSize: "0.8rem",
              marginBottom: "1.25rem",
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.1rem" }}>
          <div>
            <label className="form-label">Administrator Username</label>
            <div style={{ position: "relative" }}>
              <User
                size={16}
                style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }}
              />
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: "2.25rem" }}
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
              />
            </div>
          </div>

          <div>
            <label className="form-label">Password</label>
            <div style={{ position: "relative" }}>
              <Lock
                size={16}
                style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }}
              />
              <input
                type="password"
                className="form-input"
                style={{ paddingLeft: "2.25rem" }}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
            style={{ width: "100%", padding: "0.75rem", marginTop: "0.5rem" }}
          >
            <span>{isLoading ? "Authenticating..." : "Sign In to Lab"}</span>
            <ArrowRight size={16} />
          </button>
        </form>

        <div
          style={{
            marginTop: "1.5rem",
            paddingTop: "1.25rem",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.5rem",
            fontSize: "0.72rem",
            color: "var(--text-muted)",
          }}
        >
          <Shield size={14} style={{ color: "var(--accent-sky)" }} />
          <span>Protected with Argon2id & Encrypted Envelopes</span>
        </div>
      </div>
    </div>
  );
}
