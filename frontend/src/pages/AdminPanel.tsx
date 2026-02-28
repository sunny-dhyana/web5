import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Dispute, Order, User } from "../types";

type AdminTab = "overview" | "users" | "orders" | "disputes";

interface Stats {
  total_users: number;
  total_products: number;
  total_orders: number;
  open_disputes: number;
}

export function AdminPanel() {
  const [tab, setTab] = useState<AdminTab>("overview");
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchUser, setSearchUser] = useState("");
  const [actionMsg, setActionMsg] = useState("");
  const [selectedDispute, setSelectedDispute] = useState<Dispute | null>(null);
  const [resolution, setResolution] = useState("");
  const [refundBuyer, setRefundBuyer] = useState(true);
  const [resolveLoading, setResolveLoading] = useState(false);

  useEffect(() => {
    api.get<Stats>("/admin/stats").then(setStats).catch(console.error);
  }, []);

  useEffect(() => {
    if (tab === "users") {
      setLoading(true);
      const q = searchUser ? `?search=${encodeURIComponent(searchUser)}` : "";
      api.get<User[]>(`/admin/users${q}`).then(setUsers).finally(() => setLoading(false));
    }
    if (tab === "orders") {
      setLoading(true);
      api.get<{ items: Order[] }>("/admin/orders").then((d) => setOrders(d.items)).finally(() => setLoading(false));
    }
    if (tab === "disputes") {
      setLoading(true);
      api.get<Dispute[]>("/admin/disputes").then(setDisputes).finally(() => setLoading(false));
    }
  }, [tab, searchUser]);

  const handleFreezeToggle = async (user: User) => {
    const endpoint = user.is_frozen ? `/admin/users/${user.id}/unfreeze` : `/admin/users/${user.id}/freeze`;
    await api.put(endpoint);
    setActionMsg(`Account @${user.username} ${user.is_frozen ? "unfrozen" : "frozen"}`);
    setUsers((prev) => prev.map((u) => u.id === user.id ? { ...u, is_frozen: !u.is_frozen } : u));
  };

  const handleVerify = async (userId: number) => {
    await api.put(`/admin/users/${userId}/verify`);
    setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, is_verified: true } : u));
  };

  const handleResolveDispute = async () => {
    if (!selectedDispute || !resolution) return;
    setResolveLoading(true);
    try {
      await api.put(`/admin/disputes/${selectedDispute.id}/resolve`, {
        resolution,
        refund_buyer: refundBuyer,
      });
      setSelectedDispute(null);
      setResolution("");
      const updated = await api.get<Dispute[]>("/admin/disputes");
      setDisputes(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to resolve dispute");
    } finally {
      setResolveLoading(false);
    }
  };

  return (
    <div className="page">
      <h1 className="page-title">Admin Panel</h1>

      {actionMsg && (
        <div className="alert alert-success" onClick={() => setActionMsg("")} style={{ cursor: "pointer" }}>
          ✓ {actionMsg}
        </div>
      )}

      <div className="tab-bar">
        {(["overview", "users", "orders", "disputes"] as AdminTab[]).map((t) => (
          <button key={t} className={`tab ${tab === t ? "tab-active" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
            {t === "disputes" && stats && stats.open_disputes > 0 && (
              <span className="tab-badge">{stats.open_disputes}</span>
            )}
          </button>
        ))}
      </div>

      {tab === "overview" && stats && (
        <div className="stats-grid">
          <div className="stat-card"><span className="stat-value">{stats.total_users}</span><span className="stat-label">Total Users</span></div>
          <div className="stat-card"><span className="stat-value">{stats.total_products}</span><span className="stat-label">Active Products</span></div>
          <div className="stat-card"><span className="stat-value">{stats.total_orders}</span><span className="stat-label">Total Orders</span></div>
          <div className="stat-card stat-card-warn"><span className="stat-value">{stats.open_disputes}</span><span className="stat-label">Open Disputes</span></div>
        </div>
      )}

      {tab === "users" && (
        <div className="admin-section">
          <div className="admin-search-bar">
            <input
              type="search"
              className="form-input"
              placeholder="Search by email or username…"
              value={searchUser}
              onChange={(e) => setSearchUser(e.target.value)}
            />
          </div>
          {loading ? (
            <div className="loading-state">Loading users…</div>
          ) : (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Verified</th><th>Status</th><th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className={u.is_frozen ? "row-frozen" : ""}>
                      <td>{u.id}</td>
                      <td>@{u.username}</td>
                      <td>{u.email}</td>
                      <td><span className={`role-badge role-${u.role}`}>{u.role}</span></td>
                      <td>{u.is_verified ? "✓" : "✗"}</td>
                      <td>{u.is_frozen ? <span className="text-danger">Frozen</span> : <span className="text-success">Active</span>}</td>
                      <td className="admin-actions">
                        {!u.is_verified && (
                          <button className="btn btn-xs btn-secondary" onClick={() => handleVerify(u.id)}>Verify</button>
                        )}
                        {u.role !== "admin" && (
                          <button
                            className={`btn btn-xs ${u.is_frozen ? "btn-success" : "btn-danger"}`}
                            onClick={() => handleFreezeToggle(u)}
                          >
                            {u.is_frozen ? "Unfreeze" : "Freeze"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "orders" && (
        <div className="admin-section">
          {loading ? <div className="loading-state">Loading orders…</div> : (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr><th>ID</th><th>Buyer</th><th>Items</th><th>Total</th><th>Status</th><th>Date</th></tr>
                </thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.id}>
                      <td>#{o.id}</td>
                      <td>@{o.buyer_username}</td>
                      <td>{o.items.map((i) => `${i.product_title} ×${i.quantity}`).join(", ")}</td>
                      <td>${o.total_amount.toFixed(2)}</td>
                      <td><span className={`status-badge status-${o.status.replace("_", "-")}`}>{o.status.replace("_", " ")}</span></td>
                      <td>{new Date(o.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "disputes" && (
        <div className="admin-section">
          {loading ? <div className="loading-state">Loading disputes…</div> : (
            <>
              <div className="dispute-admin-list">
                {disputes.map((d) => (
                  <div key={d.id} className={`dispute-admin-row ${["open", "under_review"].includes(d.status) ? "dispute-open" : ""}`}>
                    <div className="dispute-admin-info">
                      <strong>Dispute #{d.id}</strong> — Order #{d.order_id}
                      <span className="text-muted">Buyer: @{d.buyer_username} / Seller: @{d.seller_username}</span>
                      <p>{d.reason.slice(0, 150)}…</p>
                    </div>
                    <div className="dispute-admin-actions">
                      <span className={`status-badge`}>{d.status.replace("_", " ")}</span>
                      {["open", "under_review"].includes(d.status) && (
                        <button className="btn btn-sm btn-primary" onClick={() => setSelectedDispute(d)}>
                          Resolve
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {selectedDispute && (
                <div className="modal-overlay" onClick={() => setSelectedDispute(null)}>
                  <div className="modal-card" onClick={(e) => e.stopPropagation()}>
                    <h2>Resolve Dispute #{selectedDispute.id}</h2>
                    <p className="text-muted">Order #{selectedDispute.order_id} — ${selectedDispute.reason.slice(0, 100)}</p>

                    <div className="form-group">
                      <label className="form-label">Resolution details</label>
                      <textarea className="form-input form-textarea" rows={3} value={resolution} onChange={(e) => setResolution(e.target.value)} placeholder="Explain the resolution…" />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Outcome</label>
                      <div className="radio-group">
                        <label><input type="radio" checked={refundBuyer} onChange={() => setRefundBuyer(true)} /> Refund buyer (escrow returned)</label>
                        <label><input type="radio" checked={!refundBuyer} onChange={() => setRefundBuyer(false)} /> Release to seller (order complete)</label>
                      </div>
                    </div>

                    <div className="modal-actions">
                      <button className="btn btn-primary" onClick={handleResolveDispute} disabled={resolveLoading || !resolution}>
                        {resolveLoading ? "Resolving…" : "Confirm Resolution"}
                      </button>
                      <button className="btn btn-secondary" onClick={() => setSelectedDispute(null)}>Cancel</button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
