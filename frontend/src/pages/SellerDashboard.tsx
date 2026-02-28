import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import type { Order, Payout, Product, Wallet } from "../types";

function SellerStats({ orders, wallet }: { orders: Order[]; wallet: Wallet | null }) {
  const completed = orders.filter((o) => o.status === "completed").length;
  const pending = orders.filter((o) => ["paid", "shipped"].includes(o.status)).length;
  const revenue = orders.filter((o) => o.status === "completed").reduce((s, o) => s + o.total_amount, 0);

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <span className="stat-value">{orders.length}</span>
        <span className="stat-label">Total Orders</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{pending}</span>
        <span className="stat-label">Pending Fulfillment</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{completed}</span>
        <span className="stat-label">Completed</span>
      </div>
      <div className="stat-card stat-card-money">
        <span className="stat-value">${wallet?.pending_balance.toFixed(2) ?? "0.00"}</span>
        <span className="stat-label">Pending Earnings</span>
      </div>
    </div>
  );
}

export function SellerDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"orders" | "products" | "payouts">("orders");
  const [payoutAmount, setPayoutAmount] = useState("");
  const [payoutLoading, setPayoutLoading] = useState(false);
  const [payoutMsg, setPayoutMsg] = useState("");
  const [payoutError, setPayoutError] = useState("");

  const fetchAll = async () => {
    const [o, p, w, pays] = await Promise.all([
      api.get<Order[]>("/orders/seller"),
      api.get<{ items: Product[] }>("/products?per_page=100"),
      api.get<Wallet>("/wallet"),
      api.get<{ items: Payout[] }>("/payouts"),
    ]);
    setOrders(o);
    setProducts(p.items.filter((pr) => pr.seller_id === user?.id));
    setWallet(w);
    setPayouts(pays.items);
  };

  useEffect(() => {
    setLoading(true);
    fetchAll().finally(() => setLoading(false));
  }, []);

  const handleShip = async (orderId: number, trackingNumber: string) => {
    await api.put(`/orders/${orderId}/ship`, { tracking_number: trackingNumber });
    fetchAll();
  };

  const handleRequestPayout = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(payoutAmount);
    if (isNaN(amount) || amount <= 0) return;

    setPayoutLoading(true);
    setPayoutError("");
    setPayoutMsg("");
    try {
      await api.post("/payouts", { amount, method: "bank_transfer" });
      setPayoutMsg(`Payout of $${amount.toFixed(2)} requested! Processing in a few seconds.`);
      setPayoutAmount("");
      setTimeout(fetchAll, 4000);
    } catch (err) {
      setPayoutError(err instanceof Error ? err.message : "Payout request failed");
    } finally {
      setPayoutLoading(false);
    }
  };

  const pendingOrders = orders.filter((o) => o.status === "paid");

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Seller Dashboard</h1>
        <button className="btn btn-primary" onClick={() => navigate("/seller/new-product")}>
          + New Product
        </button>
      </div>

      {loading ? (
        <div className="loading-state">Loading…</div>
      ) : (
        <>
          <SellerStats orders={orders} wallet={wallet} />

          {pendingOrders.length > 0 && (
            <div className="alert alert-info" style={{ marginBottom: "24px" }}>
              You have {pendingOrders.length} order{pendingOrders.length > 1 ? "s" : ""} awaiting shipment.
            </div>
          )}

          <div className="tab-bar">
            {(["orders", "products", "payouts"] as const).map((t) => (
              <button key={t} className={`tab ${tab === t ? "tab-active" : ""}`} onClick={() => setTab(t)}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {tab === "orders" && (
            <div className="seller-orders">
              {orders.length === 0 ? (
                <p className="empty-message">No orders yet.</p>
              ) : (
                orders.map((order) => (
                  <SellerOrderRow key={order.id} order={order} onShip={handleShip} />
                ))
              )}
            </div>
          )}

          {tab === "products" && (
            <div className="seller-products">
              {products.length === 0 ? (
                <div className="empty-state">
                  <p>You haven't listed any products yet.</p>
                  <button className="btn btn-primary" onClick={() => navigate("/seller/new-product")}>Create First Product</button>
                </div>
              ) : (
                products.map((p) => (
                  <div key={p.id} className="seller-product-row">
                    <div className="seller-product-info">
                      <strong>{p.title}</strong>
                      <span className="text-muted">{p.category}</span>
                    </div>
                    <div className="seller-product-meta">
                      <span>${p.price.toFixed(2)}</span>
                      <span>{p.quantity} in stock</span>
                      <span className={`status-badge ${p.is_active ? "status-completed" : "status-cancelled"}`}>
                        {p.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                    <Link to={`/seller/products/${p.id}/edit`} className="btn btn-sm btn-secondary">Edit</Link>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === "payouts" && (
            <div className="payouts-section">
              <div className="payout-request-card">
                <h3>Request Payout</h3>
                <p className="text-muted">Available: <strong>${wallet?.pending_balance.toFixed(2)}</strong></p>
                <form onSubmit={handleRequestPayout} className="payout-form">
                  <div className="form-row">
                    <input
                      type="number"
                      className="form-input"
                      placeholder="Amount"
                      value={payoutAmount}
                      onChange={(e) => setPayoutAmount(e.target.value)}
                      min="1"
                      step="0.01"
                      max={wallet?.pending_balance}
                    />
                    <button type="submit" className="btn btn-primary" disabled={payoutLoading}>
                      {payoutLoading ? "Processing…" : "Request Payout"}
                    </button>
                  </div>
                  {payoutMsg && <p className="text-success">{payoutMsg}</p>}
                  {payoutError && <p className="text-danger">{payoutError}</p>}
                </form>
              </div>

              <h3 className="section-subtitle">Payout History</h3>
              {payouts.length === 0 ? (
                <p className="empty-message">No payouts yet.</p>
              ) : (
                payouts.map((p) => (
                  <div key={p.id} className="payout-row">
                    <div>
                      <span className="payout-id">Payout #{p.id}</span>
                      <span className="payout-date">{new Date(p.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="payout-amount">${p.amount.toFixed(2)}</div>
                    <div>
                      <span className={`status-badge status-${p.status}`}>{p.status}</span>
                    </div>
                    {p.reference && <span className="payout-ref">Ref: {p.reference}</span>}
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SellerOrderRow({ order, onShip }: { order: Order; onShip: (id: number, tracking: string) => void }) {
  const [tracking, setTracking] = useState("");
  const [showShipForm, setShowShipForm] = useState(false);

  return (
    <div className="seller-order-row">
      <div className="seller-order-info">
        <Link to={`/orders/${order.id}`}><strong>Order #{order.id}</strong></Link>
        <span className="text-muted">{new Date(order.created_at).toLocaleDateString()}</span>
        <span>${order.total_amount.toFixed(2)}</span>
        <span className="text-muted">{order.items.map((i) => `${i.product_title} ×${i.quantity}`).join(", ")}</span>
      </div>
      <div className="seller-order-actions">
        <span className={`status-badge status-${order.status.replace("_", "-")}`}>{order.status.replace("_", " ")}</span>
        {order.status === "paid" && !showShipForm && (
          <button className="btn btn-sm btn-primary" onClick={() => setShowShipForm(true)}>Mark Shipped</button>
        )}
        {showShipForm && (
          <div className="ship-form">
            <input
              className="form-input form-input-sm"
              placeholder="Tracking number"
              value={tracking}
              onChange={(e) => setTracking(e.target.value)}
            />
            <button
              className="btn btn-sm btn-primary"
              onClick={() => { if (tracking) { onShip(order.id, tracking); setShowShipForm(false); } }}
            >
              Confirm
            </button>
            <button className="btn btn-sm btn-secondary" onClick={() => setShowShipForm(false)}>Cancel</button>
          </div>
        )}
      </div>
    </div>
  );
}
