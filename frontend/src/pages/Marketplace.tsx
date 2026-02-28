import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useCart } from "../contexts/CartContext";
import type { Product, ProductListResponse } from "../types";

const CATEGORIES = [
  "All", "Electronics", "Accessories", "Clothing",
  "Food & Beverage", "Education", "Books", "Home & Garden", "Sports",
];

function ProductCard({ product }: { product: Product }) {
  const { addItem } = useCart();
  const [added, setAdded] = useState(false);

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    addItem(product, 1);
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  };

  return (
    <Link to={`/products/${product.id}`} className="product-card">
      <div className="product-image-wrap">
        {product.image_url ? (
          <img src={product.image_url} alt={product.title} className="product-image" loading="lazy" />
        ) : (
          <div className="product-image-placeholder">
            <span>{product.title.charAt(0)}</span>
          </div>
        )}
        {product.product_type === "digital" && (
          <span className="product-badge badge-digital">Digital</span>
        )}
      </div>
      <div className="product-info">
        <p className="product-seller">@{product.seller_username}</p>
        <h3 className="product-title">{product.title}</h3>
        <div className="product-meta">
          {product.category && <span className="product-category">{product.category}</span>}
          <span className="product-stock">
            {product.quantity > 0 ? `${product.quantity} in stock` : "Out of stock"}
          </span>
        </div>
        <div className="product-footer">
          <span className="product-price">${product.price.toFixed(2)}</span>
          <button
            className={`btn btn-sm ${added ? "btn-success" : "btn-primary"}`}
            onClick={handleAddToCart}
            disabled={product.quantity === 0 || added}
          >
            {added ? "Added!" : "Add to Cart"}
          </button>
        </div>
      </div>
    </Link>
  );
}

export function Marketplace() {
  const [data, setData] = useState<ProductListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [category, setCategory] = useState("All");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), per_page: "12" });
    if (search) params.set("search", search);
    if (category !== "All") params.set("category", category);

    api.get<ProductListResponse>(`/products?${params}`)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [search, category, page]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const handleCategory = (cat: string) => {
    setCategory(cat);
    setPage(1);
  };

  return (
    <div className="page marketplace-page">
      <div className="marketplace-hero">
        <h1>Discover something great</h1>
        <p>Shop from thousands of sellers offering unique products</p>
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="search"
            className="search-input"
            placeholder="Search products…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">Search</button>
        </form>
      </div>

      <div className="marketplace-body">
        <aside className="marketplace-sidebar">
          <h3 className="sidebar-title">Categories</h3>
          <ul className="category-list">
            {CATEGORIES.map((cat) => (
              <li key={cat}>
                <button
                  className={`category-item ${category === cat ? "active" : ""}`}
                  onClick={() => handleCategory(cat)}
                >
                  {cat}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <div className="marketplace-main">
          <div className="marketplace-header">
            <span className="result-count">
              {data ? `${data.total} product${data.total !== 1 ? "s" : ""}` : "Loading…"}
            </span>
          </div>

          {loading ? (
            <div className="grid-skeleton">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton-card" />
              ))}
            </div>
          ) : data?.items.length === 0 ? (
            <div className="empty-state">
              <p>No products found. Try a different search or category.</p>
            </div>
          ) : (
            <div className="product-grid">
              {data?.items.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          )}

          {data && data.pages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              <span className="page-info">Page {page} of {data.pages}</span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                disabled={page === data.pages}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
