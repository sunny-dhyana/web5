import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Product } from "../types";

const CATEGORIES = [
  "Electronics", "Accessories", "Clothing", "Food & Beverage",
  "Education", "Books", "Home & Garden", "Sports", "Other",
];

export function NewProduct() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const [form, setForm] = useState({
    title: "",
    description: "",
    price: "",
    quantity: "",
    product_type: "shippable",
    category: "",
    image_url: "",
    is_active: true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isEdit) {
      api.get<Product>(`/products/${id}`).then((p) => {
        setForm({
          title: p.title,
          description: p.description || "",
          price: String(p.price),
          quantity: String(p.quantity),
          product_type: p.product_type,
          category: p.category || "",
          image_url: p.image_url || "",
          is_active: p.is_active,
        });
      });
    }
  }, [id, isEdit]);

  const update = (field: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const payload = {
      title: form.title,
      description: form.description || undefined,
      price: parseFloat(form.price),
      quantity: parseInt(form.quantity),
      product_type: form.product_type,
      category: form.category || undefined,
      image_url: form.image_url || undefined,
      is_active: form.is_active,
    };

    try {
      if (isEdit) {
        await api.put(`/products/${id}`, payload);
      } else {
        await api.post<Product>("/products", payload);
      }
      navigate("/seller");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save product");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h1 className="page-title">{isEdit ? "Edit Product" : "New Product"}</h1>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="form-card">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Product title *</label>
            <input type="text" className="form-input" value={form.title} onChange={update("title")} required minLength={3} placeholder="e.g., Handmade Ceramic Mug" />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea className="form-input form-textarea" value={form.description} onChange={update("description")} rows={4} placeholder="Describe your product in detail…" />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Price (USD) *</label>
              <input type="number" className="form-input" value={form.price} onChange={update("price")} required min="0.01" step="0.01" placeholder="0.00" />
            </div>
            <div className="form-group">
              <label className="form-label">Quantity *</label>
              <input type="number" className="form-input" value={form.quantity} onChange={update("quantity")} required min="0" placeholder="0" />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Product type *</label>
              <select className="form-input form-select" value={form.product_type} onChange={update("product_type")}>
                <option value="shippable">Physical / Shippable</option>
                <option value="digital">Digital Download</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-input form-select" value={form.category} onChange={update("category")}>
                <option value="">— Select category —</option>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Image URL</label>
            <input type="url" className="form-input" value={form.image_url} onChange={update("image_url")} placeholder="https://example.com/image.jpg" />
          </div>

          {isEdit && (
            <div className="form-group form-group-inline">
              <input type="checkbox" id="is_active" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
              <label htmlFor="is_active" className="form-label">Active (visible to buyers)</label>
            </div>
          )}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Saving…" : isEdit ? "Save Changes" : "Create Product"}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => navigate("/seller")}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
}
