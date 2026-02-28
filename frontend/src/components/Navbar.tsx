import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useCart } from "../contexts/CartContext";

export function Navbar() {
  const { user, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden>
            <circle cx="14" cy="14" r="14" fill="#2563eb" />
            <path d="M7 20L11 8l3 8 3-8 4 12" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>Mercury</span>
        </Link>

        <div className="navbar-links">
          <Link to="/" className="nav-link">Marketplace</Link>

          {user ? (
            <>
              <Link to="/wallet" className="nav-link">Wallet</Link>
              <Link to="/orders" className="nav-link">Orders</Link>
              <Link to="/disputes" className="nav-link">Disputes</Link>
              {(user.role === "seller" || user.role === "admin") && (
                <Link to="/seller" className="nav-link">Seller</Link>
              )}
              {user.role === "admin" && (
                <Link to="/admin" className="nav-link nav-link-admin">Admin</Link>
              )}
              <Link to="/cart" className="nav-link nav-cart-link">
                Cart
                {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
              </Link>
              <div className="nav-user-menu">
                <Link to="/profile" className="nav-avatar">
                  {user.username.charAt(0).toUpperCase()}
                </Link>
                <div className="nav-dropdown">
                  <div className="nav-dropdown-header">
                    <strong>{user.full_name || user.username}</strong>
                    <span>{user.email}</span>
                  </div>
                  <Link to="/profile" className="nav-dropdown-item">Profile</Link>
                  <button onClick={handleLogout} className="nav-dropdown-item nav-dropdown-logout">
                    Sign Out
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <Link to="/cart" className="nav-link nav-cart-link">
                Cart
                {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
              </Link>
              <Link to="/login" className="nav-link">Sign In</Link>
              <Link to="/register" className="btn btn-primary btn-sm">Get Started</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
