import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

export function Register() {
  const { login } = useAuth();
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    full_name: "",
    role: "buyer",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const update = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/register", form);
      try {
        await login(form.email, form.password);
        navigate("/");
      } catch (err) {
        setSuccess("Account created! You can now sign in.");
        setTimeout(() => navigate("/login"), 3000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <svg width="40" height="40" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="14" fill="#2563eb" />
            <path d="M7 20L11 8l3 8 3-8 4 12" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <h1 className="auth-title">Create your account</h1>
        <p className="auth-subtitle">Join Mercury and start buying or selling</p>

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {!success && (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Full name</label>
                <input type="text" className="form-input" value={form.full_name} onChange={update("full_name")} placeholder="Jane Smith" />
              </div>
              <div className="form-group">
                <label className="form-label">Username</label>
                <input type="text" className="form-input" value={form.username} onChange={update("username")} placeholder="jane_smith" required minLength={3} maxLength={50} pattern="[a-zA-Z0-9_]+" />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Email address</label>
              <input type="email" className="form-input" value={form.email} onChange={update("email")} placeholder="you@example.com" required />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input type="password" className="form-input" value={form.password} onChange={update("password")} placeholder="At least 8 characters" required minLength={8} />
            </div>

            <div className="form-group">
              <label className="form-label">I want to</label>
              <select className="form-input form-select" value={form.role} onChange={update("role")}>
                <option value="buyer">Buy products</option>
                <option value="seller">Sell products</option>
              </select>
            </div>

            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? "Creating account…" : "Create Account"}
            </button>
          </form>
        )}

        <p className="auth-footer">
          Already have an account?{" "}
          <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
