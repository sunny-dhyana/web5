export type UserRole = "buyer" | "seller" | "admin";

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  bio: string | null;
  profile_picture_url: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  is_frozen: boolean;
  created_at: string;
}

export type ProductType = "digital" | "shippable";

export interface Product {
  id: number;
  seller_id: number;
  title: string;
  description: string | null;
  price: number;
  quantity: number;
  product_type: ProductType;
  category: string | null;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  seller_username: string | null;
  seller_name: string | null;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export type OrderStatus =
  | "pending_payment"
  | "paid"
  | "shipped"
  | "delivered"
  | "completed"
  | "cancelled"
  | "disputed"
  | "refunded";

export interface OrderItem {
  id: number;
  product_id: number;
  seller_id: number;
  quantity: number;
  unit_price: number;
  product_title: string | null;
  product_image: string | null;
}

export interface Order {
  id: number;
  buyer_id: number;
  buyer_username: string | null;
  status: OrderStatus;
  total_amount: number;
  shipping_address: string | null;
  tracking_number: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface Wallet {
  id: number;
  user_id: number;
  balance: number;
  pending_balance: number;
  created_at: string;
}

export type TransactionType =
  | "deposit"
  | "purchase"
  | "escrow_release"
  | "escrow_refund"
  | "payout"
  | "refund_credit"
  | "admin_adjustment";

export interface Transaction {
  id: number;
  amount: number;
  transaction_type: TransactionType;
  reference_id: number | null;
  reference_type: string | null;
  description: string | null;
  balance_after: number;
  created_at: string;
}

export type DisputeStatus =
  | "open"
  | "under_review"
  | "resolved_buyer"
  | "resolved_seller"
  | "closed";

export interface DisputeMessage {
  id: number;
  dispute_id: number;
  sender_id: number;
  sender_username: string | null;
  content: string;
  created_at: string;
}

export interface Dispute {
  id: number;
  order_id: number;
  buyer_id: number;
  seller_id: number;
  buyer_username: string | null;
  seller_username: string | null;
  reason: string;
  status: DisputeStatus;
  admin_notes: string | null;
  resolution: string | null;
  created_at: string;
  resolved_at: string | null;
  messages: DisputeMessage[];
}

export type PayoutStatus = "pending" | "processing" | "completed" | "failed";

export interface Payout {
  id: number;
  seller_id: number;
  amount: number;
  status: PayoutStatus;
  method: string;
  reference: string | null;
  notes: string | null;
  created_at: string;
  processed_at: string | null;
  completed_at: string | null;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface ApiError {
  detail: string;
}

export interface DriveFile {
  id: number;
  seller_id: number;
  file_name: string;
  content_type: string | null;
  size: number;
  created_at: string;
}
