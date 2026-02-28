import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import type { Dispute, DisputeMessage } from "../types";

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  under_review: "Under Review",
  resolved_buyer: "Resolved — Buyer Refunded",
  resolved_seller: "Resolved — Seller Wins",
  closed: "Closed",
};

export function DisputeDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [sendLoading, setSendLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const refresh = () => api.get<Dispute>(`/disputes/${id}`).then(setDispute);

  useEffect(() => {
    setLoading(true);
    refresh().finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [dispute?.messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    setSendLoading(true);
    setError("");
    try {
      await api.post<DisputeMessage>(`/disputes/${id}/messages`, { content: message });
      setMessage("");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setSendLoading(false);
    }
  };

  if (loading) return <div className="page loading-state">Loading dispute…</div>;
  if (!dispute) return <div className="page">Dispute not found.</div>;

  const isResolved = ["resolved_buyer", "resolved_seller", "closed"].includes(dispute.status);

  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/disputes">Disputes</Link>
        <span>/</span>
        <span>Dispute #{dispute.id}</span>
      </nav>

      <div className="dispute-detail-layout">
        <div className="dispute-detail-main">
          <div className="dispute-detail-header">
            <div>
              <h1 className="dispute-detail-title">Dispute #{dispute.id}</h1>
              <p className="text-muted">Order <Link to={`/orders/${dispute.order_id}`}>#{dispute.order_id}</Link></p>
            </div>
            <span className={`status-badge status-badge-lg`}>{STATUS_LABELS[dispute.status] || dispute.status}</span>
          </div>

          <div className="dispute-reason-box">
            <h3>Issue reported</h3>
            <p>{dispute.reason}</p>
          </div>

          {dispute.resolution && (
            <div className="dispute-resolution-box">
              <h3>Resolution</h3>
              <p>{dispute.resolution}</p>
              {dispute.admin_notes && <p className="text-muted"><em>Admin notes: {dispute.admin_notes}</em></p>}
            </div>
          )}

          <div className="messages-section">
            <h2 className="section-subtitle">Messages</h2>
            <div className="messages-list">
              {dispute.messages.length === 0 ? (
                <p className="text-muted">No messages yet. Start the conversation.</p>
              ) : (
                dispute.messages.map((msg) => {
                  const isOwn = msg.sender_id === user?.id;
                  return (
                    <div key={msg.id} className={`message-bubble ${isOwn ? "message-own" : "message-other"}`}>
                      <div className="message-meta">
                        <strong>@{msg.sender_username}</strong>
                        <span>{new Date(msg.created_at).toLocaleString()}</span>
                      </div>
                      <p className="message-content">{msg.content}</p>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {!isResolved && (
              <form onSubmit={handleSend} className="message-form">
                {error && <div className="alert alert-error">{error}</div>}
                <textarea
                  className="form-input form-textarea"
                  rows={3}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Type your message…"
                />
                <button type="submit" className="btn btn-primary" disabled={sendLoading}>
                  {sendLoading ? "Sending…" : "Send Message"}
                </button>
              </form>
            )}
          </div>
        </div>

        <aside className="dispute-detail-sidebar">
          <div className="dispute-info-card">
            <h3>Dispute Info</h3>
            <div className="info-row"><span>Buyer</span><strong>@{dispute.buyer_username}</strong></div>
            <div className="info-row"><span>Seller</span><strong>@{dispute.seller_username}</strong></div>
            <div className="info-row"><span>Opened</span><span>{new Date(dispute.created_at).toLocaleDateString()}</span></div>
            {dispute.resolved_at && <div className="info-row"><span>Resolved</span><span>{new Date(dispute.resolved_at).toLocaleDateString()}</span></div>}
          </div>
        </aside>
      </div>
    </div>
  );
}
