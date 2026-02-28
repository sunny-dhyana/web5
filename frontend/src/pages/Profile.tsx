import { useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

export function Profile() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({ full_name: user?.full_name || "", bio: user?.bio || "", profile_picture_url: user?.profile_picture_url || "" });
  const [pwForm, setPwForm] = useState({ current_password: "", new_password: "" });
  const [profileMsg, setProfileMsg] = useState("");
  const [profileErr, setProfileErr] = useState("");
  const [pwMsg, setPwMsg] = useState("");
  const [pwErr, setPwErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [savingPw, setSavingPw] = useState(false);

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setProfileErr("");
    setProfileMsg("");
    try {
      await api.put("/users/me", form);
      await refreshUser();
      setProfileMsg("Profile updated successfully.");
    } catch (err) {
      setProfileErr(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPw(true);
    setPwErr("");
    setPwMsg("");
    try {
      await api.put("/users/me/password", pwForm);
      setPwMsg("Password changed successfully.");
      setPwForm({ current_password: "", new_password: "" });
    } catch (err) {
      setPwErr(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setSavingPw(false);
    }
  };

  if (!user) return null;

  return (
    <div className="page">
      <h1 className="page-title">Account Settings</h1>

      <div className="profile-layout">
        <div className="profile-card">
          <div className="profile-avatar">
            {user.profile_picture_url ? (
              <img src={user.profile_picture_url} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
            ) : (
              user.username.charAt(0).toUpperCase()
            )}
          </div>
          <div className="profile-identity">
            <h2>{user.full_name || user.username}</h2>
            <p className="text-muted">@{user.username}</p>
            <p className="text-muted">{user.email}</p>
            <span className={`role-badge role-${user.role}`}>{user.role}</span>
            {!user.is_verified && (
              <div className="alert alert-warning" style={{ marginTop: "12px" }}>
                Your email is not verified. Check your inbox.
              </div>
            )}
          </div>
        </div>

        <div className="profile-forms">
          <div className="form-card">
            <h2 className="form-card-title">Profile Information</h2>
            {profileMsg && <div className="alert alert-success">{profileMsg}</div>}
            {profileErr && <div className="alert alert-error">{profileErr}</div>}
            <form onSubmit={handleProfileSave}>
              <div className="form-group">
                <label className="form-label">Full name</label>
                <input type="text" className="form-input" value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} placeholder="Your name" />
              </div>
              <div className="form-group">
                <label className="form-label">Bio</label>
                <textarea className="form-input form-textarea" rows={3} value={form.bio} onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))} placeholder="Tell others about yourself…" />
              </div>
              <div className="form-group">
                <label className="form-label">Profile Picture URL</label>
                <input type="url" className="form-input" value={form.profile_picture_url} onChange={(e) => setForm((f) => ({ ...f, profile_picture_url: e.target.value }))} placeholder="https://example.com/avatar.png" />
              </div>
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Saving…" : "Save Changes"}</button>
            </form>
          </div>

          <div className="form-card">
            <h2 className="form-card-title">Change Password</h2>
            {pwMsg && <div className="alert alert-success">{pwMsg}</div>}
            {pwErr && <div className="alert alert-error">{pwErr}</div>}
            <form onSubmit={handlePasswordChange}>
              <div className="form-group">
                <label className="form-label">Current password</label>
                <input type="password" className="form-input" value={pwForm.current_password} onChange={(e) => setPwForm((f) => ({ ...f, current_password: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label className="form-label">New password</label>
                <input type="password" className="form-input" value={pwForm.new_password} onChange={(e) => setPwForm((f) => ({ ...f, new_password: e.target.value }))} required minLength={8} placeholder="At least 8 characters" />
              </div>
              <button type="submit" className="btn btn-primary" disabled={savingPw}>{savingPw ? "Updating…" : "Update Password"}</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
