import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useCart } from "../contexts/CartContext";
import type { Product } from "../types";

export function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);
  const { addItem } = useCart();
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get<Product>(`/products/${id}`)
      .then(setProduct)
      .catch(() => navigate("/"))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  if (loading) {
    return (
      <div className="page">
        <div className="product-detail-skeleton">
          <div className="skeleton skeleton-image" />
          <div className="skeleton-content">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-text" />
            <div className="skeleton skeleton-text" />
          </div>
        </div>
      </div>
    );
  }

  if (!product) return null;

  const handleAddToCart = () => {
    addItem(product, qty);
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  const handleBuyNow = () => {
    addItem(product, qty);
    navigate("/checkout");
  };

  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/">Marketplace</Link>
        {product.category && <><span>/</span><Link to={`/?category=${product.category}`}>{product.category}</Link></>}
        <span>/</span>
        <span>{product.title}</span>
      </nav>

      <div className="product-detail">
        <div className="product-detail-image-section">
          {product.image_url ? (
            <img src={product.image_url} alt={product.title} className="product-detail-image" />
          ) : (
            <div className="product-detail-image-placeholder">
              <span>{product.title.charAt(0)}</span>
            </div>
          )}
        </div>

        <div className="product-detail-info">
          <div className="product-detail-header">
            {product.category && <span className="badge badge-category">{product.category}</span>}
            {product.product_type === "digital" && <span className="badge badge-digital">Digital Download</span>}
          </div>

          <h1 className="product-detail-title">{product.title}</h1>

          <div className="product-detail-seller">
            Sold by{" "}
            <strong>@{product.seller_username}</strong>
            {product.seller_name && ` (${product.seller_name})`}
          </div>

          <div className="product-detail-price">${product.price.toFixed(2)}</div>

          {product.description && (
            <div className="product-detail-description">
              <h3>Description</h3>
              <div dangerouslySetInnerHTML={{ __html: product.description }} />
            </div>
          )}

          <div className="product-detail-stock">
            {product.quantity > 0 ? (
              <span className="in-stock">✓ In stock ({product.quantity} available)</span>
            ) : (
              <span className="out-of-stock">Out of stock</span>
            )}
          </div>

          {product.quantity > 0 && (
            <div className="product-detail-actions">
              <div className="qty-selector">
                <label>Quantity</label>
                <div className="qty-control">
                  <button onClick={() => setQty((q) => Math.max(1, q - 1))}>−</button>
                  <span>{qty}</span>
                  <button onClick={() => setQty((q) => Math.min(product.quantity, q + 1))}>+</button>
                </div>
              </div>

              <div className="product-detail-buttons">
                <button
                  className={`btn btn-full ${added ? "btn-success" : "btn-secondary"}`}
                  onClick={handleAddToCart}
                >
                  {added ? "✓ Added to cart" : "Add to Cart"}
                </button>
                <button className="btn btn-primary btn-full" onClick={handleBuyNow}>
                  Buy Now
                </button>
              </div>
            </div>
          )}

          <div className="product-detail-meta">
            <div className="meta-item">
              <span className="meta-label">Type</span>
              <span>{product.product_type === "digital" ? "Digital product" : "Physical product"}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Listed</span>
              <span>{new Date(product.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
