import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Dispute, DisputeStatus } from "../types";

const STATUS_LABELS: Record<DisputeStatus, string> = {
  open: "Open",
  under_review: "Under Review",
  resolved_buyer: "Resolved — Refunded",
  resolved_seller: "Resolved — Seller Wins",
  closed: "Closed",
};

const STATUS_CLASS: Record<DisputeStatus, string> = {
  open: "status-disputed",
  under_review: "status-shipped",
  resolved_buyer: "status-completed",
  resolved_seller: "status-completed",
  closed: "status-cancelled",
};

export function DisputeCenter() {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Dispute[]>("/disputes")
      .then(setDisputes)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <h1 className="page-title">Dispute Center</h1>
      <p className="page-subtitle">
        Disputes allow buyers and sellers to resolve order issues. Our team reviews all disputes.
      </p>

      {loading ? (
        <div className="loading-state">Loading disputes…</div>
      ) : disputes.length === 0 ? (
        <div className="empty-state centered">
          <div className="empty-icon">⚖️</div>
          <h2>No disputes</h2>
          <p>You have no active or past disputes.</p>
        </div>
      ) : (
        <div className="dispute-list">
          {disputes.map((d) => (
            <Link key={d.id} to={`/disputes/${d.id}`} className="dispute-card">
              <div className="dispute-card-header">
                <div>
                  <span className="dispute-id">Dispute #{d.id}</span>
                  <span className="dispute-order">Order #{d.order_id}</span>
                </div>
                <span className={`status-badge ${STATUS_CLASS[d.status]}`}>
                  {STATUS_LABELS[d.status]}
                </span>
              </div>
              <p className="dispute-reason">{d.reason.slice(0, 120)}{d.reason.length > 120 ? "…" : ""}</p>
              <div className="dispute-card-footer">
                <span>Buyer: @{d.buyer_username}</span>
                <span>Seller: @{d.seller_username}</span>
                <span>{new Date(d.created_at).toLocaleDateString()}</span>
                <span>{d.messages.length} message{d.messages.length !== 1 ? "s" : ""}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
