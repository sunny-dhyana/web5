import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import type { Order } from "../types";

const STATUS_LABELS: Record<string, string> = {
  pending_payment: "Pending Payment",
  paid: "Paid — Awaiting Shipment",
  shipped: "Shipped",
  delivered: "Delivered",
  completed: "Completed",
  cancelled: "Cancelled",
  disputed: "Disputed",
  refunded: "Refunded",
};

export function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [disputeReason, setDisputeReason] = useState("");
  const [showDisputeForm, setShowDisputeForm] = useState(false);

  const refresh = () =>
    api.get<Order>(`/orders/${id}`).then(setOrder).catch(() => navigate("/orders"));

  useEffect(() => {
    setLoading(true);
    refresh().finally(() => setLoading(false));
  }, [id]);

  const doAction = async (fn: () => Promise<Order>, msg: string) => {
    setActionLoading(true);
    setError("");
    setSuccess("");
    try {
      const updated = await fn();
      setOrder(updated);
      setSuccess(msg);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDelivery = () =>
    doAction(() => api.put<Order>(`/orders/${id}/confirm-delivery`), "Delivery confirmed!");

  const handleComplete = () =>
    doAction(() => api.put<Order>(`/orders/${id}/complete`), "Order completed! Payment released to seller.");

  const handleCancel = () =>
    doAction(() => api.put<Order>(`/orders/${id}/cancel`, { reason: "Cancelled by buyer" }), "Order cancelled.");

  const handleOpenDispute = async () => {
    if (!disputeReason || disputeReason.length < 20) {
      setError("Please provide a detailed reason (at least 20 characters)");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      const dispute = await api.post<{ id: number }>("/disputes", { order_id: Number(id), reason: disputeReason });
      navigate(`/disputes/${dispute.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open dispute");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="page loading-state">Loading…</div>;
  if (!order) return null;

  const isBuyer = user?.id === order.buyer_id;
  const canConfirmDelivery = isBuyer && order.status === "shipped";
  const canComplete = isBuyer && order.status === "delivered";
  const canCancel = isBuyer && ["pending_payment", "paid"].includes(order.status);
  const canDispute = isBuyer && ["paid", "shipped", "delivered"].includes(order.status);

  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/orders">My Orders</Link>
        <span>/</span>
        <span>Order #{order.id}</span>
      </nav>

      <div className="order-detail-layout">
        <div className="order-detail-main">
          <div className="order-detail-header">
            <div>
              <h1 className="order-detail-title">Order #{order.id}</h1>
              <p className="order-detail-date">Placed {new Date(order.created_at).toLocaleString()}</p>
            </div>
            <span className={`status-badge status-badge-lg status-${order.status.replace("_", "-")}`}>
              {STATUS_LABELS[order.status] || order.status}
            </span>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}

          <div className="order-items-section">
            <h2 className="section-subtitle">Items</h2>
            {order.items.map((item) => (
              <div key={item.id} className="order-detail-item">
                <div className="order-detail-item-img">
                  {item.product_image ? (
                    <img src={item.product_image} alt={item.product_title || ""} />
                  ) : (
                    <div className="placeholder-img">{(item.product_title || "P").charAt(0)}</div>
                  )}
                </div>
                <div className="order-detail-item-info">
                  <Link to={`/products/${item.product_id}`} className="order-detail-item-title">
                    {item.product_title || `Product #${item.product_id}`}
                  </Link>
                  <span>Qty: {item.quantity} × ${item.unit_price.toFixed(2)}</span>
                </div>
                <span className="order-detail-item-total">${(item.quantity * item.unit_price).toFixed(2)}</span>
              </div>
            ))}
          </div>

          {order.tracking_number && (
            <div className="tracking-section">
              <h2 className="section-subtitle">Shipping</h2>
              <p><strong>Tracking number:</strong> {order.tracking_number}</p>
              {order.shipping_address && <p><strong>Address:</strong> {order.shipping_address}</p>}
            </div>
          )}

          {isBuyer && (
            <div className="order-actions">
              {canConfirmDelivery && (
                <button className="btn btn-primary" onClick={handleConfirmDelivery} disabled={actionLoading}>
                  Confirm Delivery Received
                </button>
              )}
              {canComplete && (
                <button className="btn btn-success" onClick={handleComplete} disabled={actionLoading}>
                  Complete Order & Release Payment
                </button>
              )}
              {canCancel && (
                <button className="btn btn-danger btn-outline" onClick={handleCancel} disabled={actionLoading}>
                  Cancel Order
                </button>
              )}
              {canDispute && (
                <button className="btn btn-warning" onClick={() => setShowDisputeForm(true)}>
                  Open Dispute
                </button>
              )}
            </div>
          )}

          {showDisputeForm && (
            <div className="dispute-form-card">
              <h3>Open a Dispute</h3>
              <p className="text-muted">Describe the issue with your order in detail.</p>
              <textarea
                className="form-input form-textarea"
                rows={4}
                value={disputeReason}
                onChange={(e) => setDisputeReason(e.target.value)}
                placeholder="Describe the issue (min 20 characters)…"
              />
              <div className="form-actions">
                <button className="btn btn-primary" onClick={handleOpenDispute} disabled={actionLoading}>
                  Submit Dispute
                </button>
                <button className="btn btn-secondary" onClick={() => setShowDisputeForm(false)}>Cancel</button>
              </div>
            </div>
          )}
        </div>

        <aside className="order-detail-sidebar">
          <div className="order-summary-card">
            <h2 className="section-subtitle">Summary</h2>
            <div className="summary-row"><span>Subtotal</span><span>${order.total_amount.toFixed(2)}</span></div>
            <div className="summary-total"><span>Total</span><span>${order.total_amount.toFixed(2)}</span></div>
          </div>

          {order.shipping_address && (
            <div className="order-address-card">
              <h3 className="section-subtitle">Ship To</h3>
              <p>{order.shipping_address}</p>
            </div>
          )}

          {order.notes && (
            <div className="order-notes-card">
              <h3 className="section-subtitle">Notes</h3>
              <p>{order.notes}</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
