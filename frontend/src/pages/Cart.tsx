import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../contexts/CartContext";
import { useAuth } from "../contexts/AuthContext";

export function Cart() {
  const { items, removeItem, updateQuantity, totalAmount } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();

  if (items.length === 0) {
    return (
      <div className="page">
        <div className="empty-state centered">
          <div className="empty-icon">🛒</div>
          <h2>Your cart is empty</h2>
          <p>Browse the marketplace to find products you love.</p>
          <Link to="/" className="btn btn-primary">Browse Marketplace</Link>
        </div>
      </div>
    );
  }

  const sellerGroups = items.reduce<Record<string, typeof items>>((groups, item) => {
    const seller = item.product.seller_username || "Unknown";
    if (!groups[seller]) groups[seller] = [];
    groups[seller].push(item);
    return groups;
  }, {});

  const multiSeller = Object.keys(sellerGroups).length > 1;

  return (
    <div className="page">
      <h1 className="page-title">Shopping Cart</h1>

      <div className="cart-layout">
        <div className="cart-items">
          {multiSeller && (
            <div className="alert alert-warning">
              Items from multiple sellers will create separate orders at checkout.
            </div>
          )}

          {Object.entries(sellerGroups).map(([seller, sellerItems]) => (
            <div key={seller} className="cart-seller-group">
              <div className="cart-seller-header">Seller: @{seller}</div>
              {sellerItems.map(({ product, quantity }) => (
                <div key={product.id} className="cart-item">
                  <div className="cart-item-image">
                    {product.image_url ? (
                      <img src={product.image_url} alt={product.title} />
                    ) : (
                      <div className="cart-item-placeholder">{product.title.charAt(0)}</div>
                    )}
                  </div>
                  <div className="cart-item-info">
                    <Link to={`/products/${product.id}`} className="cart-item-title">{product.title}</Link>
                    <span className="cart-item-price">${product.price.toFixed(2)} each</span>
                    {product.product_type === "digital" && (
                      <span className="badge badge-digital badge-sm">Digital</span>
                    )}
                  </div>
                  <div className="cart-item-controls">
                    <div className="qty-control">
                      <button onClick={() => updateQuantity(product.id, quantity - 1)}>−</button>
                      <span>{quantity}</span>
                      <button onClick={() => updateQuantity(product.id, Math.min(product.quantity, quantity + 1))}>+</button>
                    </div>
                    <span className="cart-item-subtotal">${(product.price * quantity).toFixed(2)}</span>
                    <button className="btn-icon-danger" onClick={() => removeItem(product.id)} title="Remove">✕</button>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        <aside className="cart-summary">
          <h2 className="summary-title">Order Summary</h2>
          <div className="summary-row">
            <span>Items ({items.reduce((s, i) => s + i.quantity, 0)})</span>
            <span>${totalAmount.toFixed(2)}</span>
          </div>
          <div className="summary-row">
            <span>Shipping</span>
            <span className="text-muted">Calculated at checkout</span>
          </div>
          <div className="summary-total">
            <span>Total</span>
            <span>${totalAmount.toFixed(2)}</span>
          </div>

          {user ? (
            <button className="btn btn-primary btn-full" onClick={() => navigate("/checkout")}>
              Proceed to Checkout
            </button>
          ) : (
            <Link to="/login" state={{ from: { pathname: "/checkout" } }} className="btn btn-primary btn-full text-center">
              Sign in to Checkout
            </Link>
          )}

          <Link to="/" className="btn btn-secondary btn-full" style={{ marginTop: "8px" }}>
            Continue Shopping
          </Link>
        </aside>
      </div>
    </div>
  );
}
