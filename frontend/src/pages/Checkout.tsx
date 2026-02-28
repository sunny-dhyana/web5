import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { useCart } from "../contexts/CartContext";
import type { Order, Wallet } from "../types";

export function Checkout() {
  const { items, clearCart, totalAmount } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Wallet>("/wallet").then(setWallet).catch(console.error);
  }, []);

  useEffect(() => {
    if (items.length === 0) navigate("/cart");
  }, [items, navigate]);

  const sellerGroups = items.reduce<Record<number, typeof items>>((groups, item) => {
    const sid = item.product.seller_id;
    if (!groups[sid]) groups[sid] = [];
    groups[sid].push(item);
    return groups;
  }, {});

  const hasPhysicalItems = items.some((i) => i.product.product_type === "shippable");

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (hasPhysicalItems && !address.trim()) {
      setError("Shipping address is required for physical items");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const orders: Order[] = [];

      for (const sellerItems of Object.values(sellerGroups)) {
        const orderItems = sellerItems.map((i) => ({
          product_id: i.product.id,
          quantity: i.quantity,
        }));

        const order = await api.post<Order>("/orders", {
          items: orderItems,
          shipping_address: address || undefined,
          notes: notes || undefined,
        });

        orders.push(order);
      }

      clearCart();
      navigate("/orders", { state: { newOrders: orders.map((o) => o.id) } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setLoading(false);
    }
  };

  const insufficientBalance = wallet && wallet.balance < totalAmount;

  return (
    <div className="page">
      <h1 className="page-title">Checkout</h1>

      <div className="checkout-layout">
        <div className="checkout-form-section">
          <form onSubmit={handlePlaceOrder}>
            {hasPhysicalItems && (
              <div className="checkout-section">
                <h2 className="section-title">Shipping Information</h2>
                <div className="form-group">
                  <label className="form-label">Delivery address *</label>
                  <textarea
                    className="form-input form-textarea"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Street, City, State, ZIP, Country"
                    rows={3}
                    required={hasPhysicalItems}
                  />
                </div>
              </div>
            )}

            <div className="checkout-section">
              <h2 className="section-title">Payment</h2>
              <div className="wallet-balance-card">
                <div className="wallet-balance-info">
                  <span className="wallet-label">Mercury Wallet Balance</span>
                  <span className={`wallet-amount ${insufficientBalance ? "text-danger" : "text-success"}`}>
                    ${wallet ? wallet.balance.toFixed(2) : "—"}
                  </span>
                </div>
                {insufficientBalance && (
                  <div className="alert alert-error" style={{ marginTop: "12px" }}>
                    Insufficient balance. Please{" "}
                    <a href="/wallet" onClick={(e) => { e.preventDefault(); navigate("/wallet"); }}>
                      add funds to your wallet
                    </a>{" "}
                    before checkout.
                  </div>
                )}
              </div>
            </div>

            <div className="checkout-section">
              <h2 className="section-title">Notes (optional)</h2>
              <textarea
                className="form-input form-textarea"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any special instructions for the seller…"
                rows={2}
              />
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={loading || !!insufficientBalance}
            >
              {loading ? "Placing order…" : `Place Order — $${totalAmount.toFixed(2)}`}
            </button>
          </form>
        </div>

        <aside className="checkout-summary">
          <h2 className="section-title">Order Review</h2>

          {Object.entries(sellerGroups).map(([sid, sellerItems]) => (
            <div key={sid} className="checkout-seller-group">
              <p className="checkout-seller-label">@{sellerItems[0].product.seller_username}</p>
              {sellerItems.map(({ product, quantity }) => (
                <div key={product.id} className="checkout-item">
                  <span className="checkout-item-name">
                    {product.title}
                    <span className="checkout-item-qty"> ×{quantity}</span>
                  </span>
                  <span>${(product.price * quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>
          ))}

          <div className="summary-divider" />
          <div className="summary-total">
            <span>Total</span>
            <span>${totalAmount.toFixed(2)}</span>
          </div>

          <div className="checkout-trust">
            <p>🔒 Funds are held in escrow until delivery is confirmed</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
