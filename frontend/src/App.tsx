import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";
import { CartProvider } from "./contexts/CartContext";
import { AdminPanel } from "./pages/AdminPanel";
import { Cart } from "./pages/Cart";
import { Checkout } from "./pages/Checkout";
import { DisputeCenter } from "./pages/DisputeCenter";
import { DisputeDetail } from "./pages/DisputeDetail";
import { ForgotPassword } from "./pages/ForgotPassword";
import { Login } from "./pages/Login";
import { Marketplace } from "./pages/Marketplace";
import { NewProduct } from "./pages/NewProduct";
import { OrderDetail } from "./pages/OrderDetail";
import { Orders } from "./pages/Orders";
import { ProductDetail } from "./pages/ProductDetail";
import { Profile } from "./pages/Profile";
import { Register } from "./pages/Register";
import { ResetPassword } from "./pages/ResetPassword";
import { SellerDashboard } from "./pages/SellerDashboard";
import { WalletDashboard } from "./pages/WalletDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CartProvider>
          <Routes>
            <Route element={<Layout />}>
              {/* Public */}
              <Route path="/" element={<Marketplace />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/products/:id" element={<ProductDetail />} />
              <Route path="/cart" element={<Cart />} />

              {/* Buyer */}
              <Route path="/checkout" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
              <Route path="/orders" element={<ProtectedRoute><Orders /></ProtectedRoute>} />
              <Route path="/orders/:id" element={<ProtectedRoute><OrderDetail /></ProtectedRoute>} />
              <Route path="/wallet" element={<ProtectedRoute><WalletDashboard /></ProtectedRoute>} />
              <Route path="/disputes" element={<ProtectedRoute><DisputeCenter /></ProtectedRoute>} />
              <Route path="/disputes/:id" element={<ProtectedRoute><DisputeDetail /></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />

              {/* Seller */}
              <Route path="/seller" element={<ProtectedRoute requiredRole="seller"><SellerDashboard /></ProtectedRoute>} />
              <Route path="/seller/new-product" element={<ProtectedRoute requiredRole="seller"><NewProduct /></ProtectedRoute>} />
              <Route path="/seller/products/:id/edit" element={<ProtectedRoute requiredRole="seller"><NewProduct /></ProtectedRoute>} />

              {/* Admin */}
              <Route path="/admin" element={<ProtectedRoute requiredRole="admin"><AdminPanel /></ProtectedRoute>} />
            </Route>
          </Routes>
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
