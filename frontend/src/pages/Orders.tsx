import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api/client";
import type { Order, OrderStatus } from "../types";

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending_payment: "Pending Payment",
  paid: "Paid",
  shipped: "Shipped",
  delivered: "Delivered",
  completed: "Completed",
  cancelled: "Cancelled",
  disputed: "Disputed",
  refunded: "Refunded",
};

const STATUS_CLASS: Record<OrderStatus, string> = {
  pending_payment: "status-pending",
  paid: "status-paid",
  shipped: "status-shipped",
  delivered: "status-delivered",
  completed: "status-completed",
  cancelled: "status-cancelled",
  disputed: "status-disputed",
  refunded: "status-refunded",
};

function OrderCard({ order }: { order: Order }) {
  return (
    <Link to={`/orders/${order.id}`} className="order-card">
      <div className="order-card-header">
        <div>
          <span className="order-id">Order #{order.id}</span>
          <span className="order-date">{new Date(order.created_at).toLocaleDateString()}</span>
        </div>
        <span className={`status-badge ${STATUS_CLASS[order.status]}`}>
          {STATUS_LABELS[order.status]}
        </span>
      </div>

      <div className="order-items-preview">
        {order.items.map((item) => (
          <span key={item.id} className="order-item-chip">
            {item.product_title} ×{item.quantity}
          </span>
        ))}
      </div>

      <div className="order-card-footer">
        <span className="order-total">${order.total_amount.toFixed(2)}</span>
        {order.tracking_number && (
          <span className="order-tracking">Tracking: {order.tracking_number}</span>
        )}
      </div>
    </Link>
  );
}

export function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const location = useLocation();
  const newOrders = (location.state as { newOrders?: number[] })?.newOrders;

  useEffect(() => {
    setLoading(true);
    const params = statusFilter !== "all" ? `?status=${statusFilter}` : "";
    api.get<Order[]>(`/orders${params}`)
      .then(setOrders)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  const statusOptions: Array<{ value: string; label: string }> = [
    { value: "all", label: "All Orders" },
    ...Object.entries(STATUS_LABELS).map(([v, l]) => ({ value: v, label: l })),
  ];

  return (
    <div className="page">
      <h1 className="page-title">My Orders</h1>

      {newOrders && newOrders.length > 0 && (
        <div className="alert alert-success">
          ✓ Order{newOrders.length > 1 ? "s" : ""} placed successfully! (#{newOrders.join(", #")})
        </div>
      )}

      <div className="filter-bar">
        <select
          className="form-input form-select filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {statusOptions.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="loading-state">Loading orders…</div>
      ) : orders.length === 0 ? (
        <div className="empty-state centered">
          <div className="empty-icon">📦</div>
          <h2>No orders found</h2>
          <p>Your orders will appear here once you make a purchase.</p>
          <Link to="/" className="btn btn-primary">Start Shopping</Link>
        </div>
      ) : (
        <div className="order-list">
          {orders.map((o) => <OrderCard key={o.id} order={o} />)}
        </div>
      )}
    </div>
  );
}
